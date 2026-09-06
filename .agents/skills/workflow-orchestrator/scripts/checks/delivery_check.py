#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import emit, load_object, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, default=Path("paper"))
    parser.add_argument("--format", choices=("latex", "word", "markdown"), default="latex")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.paper_root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks = {"paper_root": str(root), "format": args.format}
    if args.format == "latex":
        shared = Path(__file__).resolve().parents[3] / "latex-paper-zh/scripts"
        sys.path.insert(0, str(shared))
        from check_latex_delivery import check
        actual, code = check(root / "main.tex")
        if code:
            errors.extend(actual["errors"])
        required = [root / "main.tex", root / "main.pdf", root / "latex_build_report.json", root / "latex_delivery_check.json"]
        for path in required:
            checks[path.name] = path.exists() and path.stat().st_size > 0
            if not checks[path.name]:
                errors.append(f"missing delivery artifact: {path.name}")
        for report_name in ("latex_build_report.json", "latex_delivery_check.json"):
            path = root / report_name
            if path.exists():
                try:
                    value = load_object(path)
                except (OSError, ValueError):
                    errors.append(f"invalid report: {report_name}")
                else:
                    status = value.get("status")
                    if report_name == "latex_build_report.json" and status != "passed":
                        errors.append(f"LaTeX build status is {status}")
                    if report_name == "latex_delivery_check.json" and status not in {"passed", "passed_with_visual_check_pending"}:
                        errors.append(f"LaTeX delivery status is {status}")
        warnings.append("PDF page rendering still requires visual verification")
    elif args.format == "word":
        if not any(root.glob("*.docx")):
            errors.append("no Word document found")
    else:
        if not any(root.glob("*.md")):
            errors.append("no Markdown paper found")
    return emit(report("delivery_check", errors, warnings, checks), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
