#!/usr/bin/env python3
"""Check LaTeX logs and final PDF existence without claiming visual correctness."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FATAL_PATTERNS = {
    "latex_error": re.compile(r"! LaTeX Error:"),
    "undefined_control_sequence": re.compile(r"Undefined control sequence"),
    "missing_file": re.compile(r"LaTeX Error: File `[^']+' not found"),
    "undefined_references": re.compile(r"There were undefined references"),
    "undefined_citations": re.compile(r"Citation .* undefined"),
}


def check(main_tex: Path) -> tuple[dict, int]:
    main_tex = main_tex.resolve()
    pdf = main_tex.with_suffix(".pdf")
    log = main_tex.with_suffix(".log")
    result = {
        "schema_version": 1,
        "main_tex": str(main_tex),
        "pdf": str(pdf),
        "log": str(log),
        "status": "failed",
        "checks": {},
        "warnings": [],
        "errors": [],
        "visual_render_check_required": True,
    }
    result["checks"]["tex_exists"] = main_tex.exists() and main_tex.stat().st_size > 0
    result["checks"]["pdf_exists"] = pdf.exists() and pdf.stat().st_size > 0
    if not result["checks"]["tex_exists"]:
        result["errors"].append("main TeX file is missing or empty")
    if not result["checks"]["pdf_exists"]:
        result["errors"].append("final PDF is missing or empty")

    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    result["checks"]["log_exists"] = log.exists()
    for name, pattern in FATAL_PATTERNS.items():
        count = len(pattern.findall(log_text))
        result["checks"][name] = count
        if count:
            result["errors"].append(f"{name}: {count}")
    overfull = len(re.findall(r"Overfull \\hbox", log_text))
    result["checks"]["overfull_hbox"] = overfull
    if overfull:
        result["warnings"].append(f"Overfull hbox: {overfull}; inspect rendered pages")

    if not result["errors"]:
        result["status"] = "passed_with_visual_check_pending"
    return result, 0 if not result["errors"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("main_tex", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result, code = check(args.main_tex)
    report_path = args.report or args.main_tex.resolve().parent / "latex_delivery_check.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
