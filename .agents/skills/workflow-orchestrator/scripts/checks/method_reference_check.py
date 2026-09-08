#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, load_object, report


REFERENCE_ROLES = {
    "empirical_baseline", "heuristic", "historical", "previous_policy",
    "small_instance_oracle", "analytic_check", "none_with_reason",
}
CONTRACT_KEYS = ("data_hash", "split_hash", "feature_spec_hash", "metric_definition_hash")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("--method-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run = load_object(args.summary)
    method = load_object(args.method_contract)
    errors: list[str] = []
    warnings: list[str] = []

    methods = [row for row in run.get("methods", []) if isinstance(row, dict)]
    main = next((row for row in methods if row.get("role") == "main"), None)
    if not main:
        errors.append("missing main method result")
    elif main.get("status") != "success" or not main.get("output_files"):
        errors.append("main method did not produce successful, traceable output")

    policy = method.get("reference_policy", {})
    if isinstance(policy, str):
        policy = {"role": policy}
    role = policy.get("role")
    if role not in REFERENCE_ROLES:
        errors.append("invalid reference role")
    comparison_claimed = bool(run.get("comparison_claims"))
    required = bool(policy.get("required")) or comparison_claimed
    if role == "none_with_reason":
        if not policy.get("reason"):
            errors.append("none_with_reason requires a reason")
        if comparison_claimed:
            errors.append("comparison claims require an executed reference")
    elif required:
        reference = next((row for row in methods if row.get("role") in REFERENCE_ROLES - {"none_with_reason"}), None)
        if not reference or reference.get("status") != "success" or not reference.get("output_files"):
            errors.append("required reference did not produce successful, traceable output")
        contract = run.get("comparison_contract", {})
        missing = [key for key in CONTRACT_KEYS if not isinstance(contract, dict) or not contract.get(key)]
        if missing:
            errors.append("comparison contract missing: " + ", ".join(missing))
        if run.get("comparison", {}).get("comparable") is False:
            errors.append("run marks the comparison as incomparable")
    elif not any(row.get("role") in REFERENCE_ROLES - {"none_with_reason"} for row in methods):
        warnings.append("optional reference was not executed")

    return emit(report("method_reference_check", errors, warnings, {
        "reference_role": role, "required": required, "comparison_claimed": comparison_claimed,
    }), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
