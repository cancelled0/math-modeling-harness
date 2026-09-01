#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, load_object, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_object(args.summary)
    errors: list[str] = []
    warnings: list[str] = []
    methods = data.get("methods", [])
    successful = [item for item in methods if isinstance(item, dict) and item.get("status") == "success"]
    if len(successful) < 2:
        errors.append("fewer than two successful comparable roles")
    for item in successful:
        if not item.get("output_files"):
            errors.append(f"{item.get('method_id')}: no output_files")
        if item.get("degeneracy_check") is None:
            warnings.append(f"{item.get('method_id')}: output degeneracy check not recorded")
    fallback = data.get("fallback_trigger")
    if not isinstance(fallback, dict):
        warnings.append("fallback trigger state is not recorded")
    return emit(report("modeling_coverage_check", errors, warnings, {"successful_roles": [item.get("role") for item in successful]}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
