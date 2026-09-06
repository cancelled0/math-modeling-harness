#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, load_object, report


CONTRACT_KEYS = ("data_hash", "split_hash", "feature_spec_hash", "metric_definition_hash")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_object(args.summary)
    methods = data.get("methods", [])
    errors: list[str] = []
    warnings: list[str] = []
    roles = {item.get("role"): item for item in methods if isinstance(item, dict)}
    for role in ("main", "usable_baseline"):
        if role not in roles:
            errors.append(f"missing method role: {role}")
        elif roles[role].get("status") != "success":
            errors.append(f"{role} did not complete successfully")
        elif not roles[role].get("metrics_summary"):
            errors.append(f"{role} has no metric summary")
    contract = data.get("comparison_contract", {})
    missing = [key for key in CONTRACT_KEYS if not contract.get(key)] if isinstance(contract, dict) else list(CONTRACT_KEYS)
    if missing:
        errors.append("comparison contract missing: " + ", ".join(missing))
    if data.get("comparison", {}).get("comparable") is False:
        errors.append("run summary marks main and baseline as incomparable")
    if not data.get("primary_metric"):
        warnings.append("primary_metric is not structured; automated direction comparison is unavailable")
    return emit(report("baseline_check", errors, warnings, {"roles": sorted(roles), "contract": contract}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
