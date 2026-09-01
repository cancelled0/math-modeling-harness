#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, load_object, report, resolve_inside


def entries(value: dict) -> list[dict]:
    raw = value.get("claims", value.get("frozen_numbers", value.get("items", [])))
    if isinstance(raw, dict):
        return [dict(item, claim_id=key) if isinstance(item, dict) else {"claim_id": key, "value": item} for key, item in raw.items()]
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("claims", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_object(args.claims)
    errors: list[str] = []
    checked = []
    for item in entries(data):
        source = item.get("source_file")
        locator = item.get("source_locator")
        ok = bool(source and locator)
        if ok:
            try:
                ok = resolve_inside(args.workspace.resolve(), source).exists()
            except ValueError:
                ok = False
        checked.append({"claim_id": item.get("claim_id"), "source_resolves": ok})
        if not ok:
            errors.append(f"claim source does not resolve: {item.get('claim_id')}")
    if not checked:
        errors.append("no structured claims found")
    return emit(report("claim_code_check", errors, [], {"claims": checked}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
