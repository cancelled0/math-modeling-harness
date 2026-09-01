#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import emit, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex", type=Path)
    parser.add_argument("--bib", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    citations: set[str] = set()
    bib_keys: set[str] = set()
    if args.tex:
        if not args.tex.exists():
            errors.append("TeX file does not exist")
        else:
            text = args.tex.read_text(encoding="utf-8", errors="replace")
            for group in re.findall(r"\\cite\w*\{([^}]+)\}", text):
                citations.update(key.strip() for key in group.split(",") if key.strip())
    if args.bib:
        if not args.bib.exists():
            errors.append("BibTeX file does not exist")
        else:
            bib_keys.update(re.findall(r"@[A-Za-z]+\s*\{\s*([^,\s]+)", args.bib.read_text(encoding="utf-8", errors="replace")))
    if args.tex and not args.bib and citations:
        errors.append("citations exist but no bibliography was supplied")
    missing = sorted(citations - bib_keys)
    if missing:
        errors.append("missing bibliography keys: " + ", ".join(missing))
    unused = sorted(bib_keys - citations)
    if unused:
        warnings.append(f"unused bibliography entries: {len(unused)}")
    return emit(report("reference_check", errors, warnings, {"citations": sorted(citations), "bib_keys": sorted(bib_keys), "missing": missing}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
