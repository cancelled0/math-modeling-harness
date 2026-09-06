#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, json_locator, load_object, report, resolve_inside
from claim_code_check import entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("freeze", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_object(args.freeze)
    errors: list[str] = []
    checked = []
    for item in entries(data):
        claim_id = item.get("claim_id")
        try:
            source = resolve_inside(args.workspace.resolve(), item["source_file"])
            source_data = load_object(source)
            actual = json_locator(source_data, item["source_locator"])
            matches = actual == item.get("value")
        except (KeyError, ValueError, OSError):
            matches = False
        checked.append({"claim_id": claim_id, "matches_source": matches})
        if not matches:
            errors.append(f"frozen value does not match source: {claim_id}")
        if not item.get("decision_id"):
            errors.append(f"frozen value lacks decision_id: {claim_id}")
    if not checked:
        errors.append("no frozen values found")
    return emit(report("frozen_number_check", errors, [], {"claims": checked}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
