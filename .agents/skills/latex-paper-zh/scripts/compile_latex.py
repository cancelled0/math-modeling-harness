#!/usr/bin/env python3
"""Compile a Chinese LaTeX paper and emit an auditable JSON report."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def locate(name: str) -> str | None:
    custom = os.environ.get("MODELING_TEX_BIN")
    if custom:
        candidate = Path(custom) / (name + (".exe" if os.name == "nt" else ""))
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def compiler_environment() -> dict[str, str]:
    environment = dict(os.environ)
    custom = os.environ.get("MODELING_TEX_BIN")
    if custom:
        environment["PATH"] = custom + os.pathsep + environment.get("PATH", "")
    return environment


def unavailable_runtime(output: str) -> bool:
    normalized = output.lower()
    markers = (
        "fresh tex installation",
        "finish the setup before proceeding",
        "miktex updates",
        "miktex has not been configured",
    )
    return any(marker in normalized for marker in markers)


def tail(text: str, lines: int = 120) -> str:
    return "\n".join(text.splitlines()[-lines:])


def compile_tex(main: Path, engine: str, timeout: int) -> tuple[dict, int]:
    main = main.resolve()
    report = {
        "schema_version": 1,
        "main_tex": str(main),
        "requested_engine": engine,
        "engine": None,
        "status": "failed",
        "commands": [],
        "pdf": str(main.with_suffix(".pdf")),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "warnings": [],
        "errors": [],
    }
    if not main.exists():
        report["errors"].append("main TeX file does not exist")
        return report, 1

    latexmk = locate("latexmk")
    xelatex = locate("xelatex")
    if engine == "latexmk" and (not latexmk or not xelatex):
        report["status"] = "unavailable"
        report["errors"].append("latexmk with xelatex is not available")
        return report, 2
    if engine == "xelatex" and not xelatex:
        report["status"] = "unavailable"
        report["errors"].append("xelatex is not available")
        return report, 2
    if engine == "auto":
        engine = "latexmk" if latexmk and xelatex else "xelatex" if xelatex else "unavailable"
    if engine == "unavailable":
        report["status"] = "unavailable"
        report["errors"].append("neither latexmk nor xelatex is available; set MODELING_TEX_BIN or install a TeX distribution")
        return report, 2

    report["engine"] = engine
    if engine == "latexmk":
        commands = [[latexmk, "-xelatex", "-interaction=nonstopmode", "-halt-on-error", main.name]]
    else:
        commands = [
            [xelatex, "-interaction=nonstopmode", "-halt-on-error", main.name],
            [xelatex, "-interaction=nonstopmode", "-halt-on-error", main.name],
        ]

    for command in commands:
        try:
            process = subprocess.run(
                command,
                cwd=main.parent,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                env=compiler_environment(),
            )
        except subprocess.TimeoutExpired:
            report["errors"].append(f"compile timed out after {timeout} seconds")
            return report, 1
        report["commands"].append({
            "argv": command,
            "returncode": process.returncode,
            "stdout_tail": tail(process.stdout),
            "stderr_tail": tail(process.stderr),
        })
        if process.returncode:
            combined = process.stdout + "\n" + process.stderr
            if unavailable_runtime(combined):
                report["status"] = "unavailable"
                report["errors"].append("TeX executable exists but the MiKTeX runtime is not initialized")
                return report, 2
            report["errors"].append(f"compiler returned {process.returncode}")
            return report, 1

    pdf = main.with_suffix(".pdf")
    if not pdf.exists() or pdf.stat().st_size == 0:
        report["errors"].append("compiler returned success but PDF is missing or empty")
        return report, 1
    report["status"] = "passed"
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    return report, 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("main_tex", type=Path)
    parser.add_argument("--engine", choices=("auto", "latexmk", "xelatex"), default="auto")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report, code = compile_tex(args.main_tex, args.engine, args.timeout)
    report_path = args.report or args.main_tex.resolve().parent / "latex_build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
