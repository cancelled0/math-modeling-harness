#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from _common import emit, report


def locate_tex(name: str) -> str | None:
    custom = os.environ.get("MODELING_TEX_BIN")
    if custom:
        candidate = Path(custom) / (name + (".exe" if os.name == "nt" else ""))
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def locate_pandoc() -> str | None:
    custom = os.environ.get("MODELING_PANDOC")
    if custom:
        candidate = Path(custom)
        if candidate.is_dir():
            candidate = candidate / ("pandoc.exe" if os.name == "nt" else "pandoc")
        if candidate.is_file():
            return str(candidate)
    return shutil.which("pandoc")


def locate_word() -> str | None:
    on_path = shutil.which("winword")
    if on_path:
        return on_path
    if os.name != "nt":
        return None
    candidates = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if root:
            candidates.extend([
                Path(root) / "Microsoft Office" / "Root" / "Office16" / "WINWORD.EXE",
                Path(root) / "Microsoft Office" / "Office16" / "WINWORD.EXE",
            ])
    return str(next((path for path in candidates if path.is_file()), "")) or None


def operational(command: str | None) -> tuple[bool, str | None]:
    if not command:
        return False, None
    try:
        probe = subprocess.run(
            [command, "--version"], text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    detail = (probe.stdout + "\n" + probe.stderr).strip()
    return probe.returncode == 0, detail[-1000:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--language", choices=("auto", "python", "matlab"), default="auto")
    parser.add_argument("--paper-format", choices=("none", "latex", "word", "markdown"), default="none")
    parser.add_argument(
        "--delivery-mode", choices=("single", "latex_primary_docx_mirror"), default="single"
    )
    parser.add_argument("--packages", nargs="*", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    capabilities = {
        "python": sys.executable,
        "git": shutil.which("git"),
        "matlab": shutil.which("matlab"),
        "xelatex": locate_tex("xelatex"),
        "latexmk": locate_tex("latexmk"),
        "pandoc": locate_pandoc(),
        "docx_visual_renderer": shutil.which("soffice") or shutil.which("libreoffice"),
        "microsoft_word": locate_word(),
        "packages": {name: importlib.util.find_spec(name) is not None for name in args.packages},
    }
    if not capabilities["git"]:
        errors.append("git is unavailable")
    else:
        probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=args.workspace, capture_output=True, text=True)
        capabilities["git_repository"] = probe.returncode == 0 and probe.stdout.strip() == "true"
        if not capabilities["git_repository"]:
            errors.append("workspace is not inside a Git repository")
    if args.language == "matlab" and not capabilities["matlab"]:
        errors.append("MATLAB runtime is unavailable")
    if args.paper_format == "latex":
        tex_ok, tex_probe = operational(capabilities["xelatex"])
        latexmk_ok, latexmk_probe = operational(capabilities["latexmk"])
        capabilities["xelatex_operational"] = tex_ok
        capabilities["xelatex_probe_tail"] = tex_probe
        capabilities["latexmk_operational"] = latexmk_ok
        capabilities["latexmk_probe_tail"] = latexmk_probe
        if not tex_ok:
            errors.append("Chinese LaTeX requested but xelatex is missing or not initialized")
        if tex_ok and capabilities["latexmk"] and not latexmk_ok:
            warnings.append("latexmk is present but not operational; compilation will fall back to direct XeLaTeX passes")
    if args.delivery_mode == "latex_primary_docx_mirror":
        pandoc_ok, pandoc_probe = operational(capabilities["pandoc"])
        capabilities["pandoc_operational"] = pandoc_ok
        capabilities["pandoc_probe_tail"] = pandoc_probe
        if args.paper_format != "latex":
            errors.append("latex_primary_docx_mirror requires paper format latex")
        if not pandoc_ok:
            errors.append("DOCX mirror requested but Pandoc is missing or not operational")
        if not capabilities["docx_visual_renderer"]:
            if capabilities["microsoft_word"]:
                warnings.append("automated LibreOffice rendering is unavailable; Microsoft Word is available for manual visual page QA")
            else:
                warnings.append("LibreOffice is unavailable; DOCX structural QA can run, but visual page QA remains pending")
    missing_packages = [name for name, present in capabilities["packages"].items() if not present]
    if missing_packages:
        errors.append("missing Python packages: " + ", ".join(missing_packages))
    if args.language == "auto" and not capabilities["matlab"]:
        warnings.append("MATLAB unavailable; automatic implementation will use Python")
    return emit(report("environment_check", errors, warnings, capabilities), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
