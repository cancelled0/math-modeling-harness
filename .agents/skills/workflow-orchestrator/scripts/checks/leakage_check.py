#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, load_object, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = load_object(args.contract)
    errors: list[str] = []
    warnings: list[str] = []
    split = data.get("split", data.get("comparison_contract", {}).get("split", {}))
    preprocessing = data.get("preprocessing", {})
    strategy = split.get("strategy") if isinstance(split, dict) else None
    fit_scope = preprocessing.get("fit_scope") if isinstance(preprocessing, dict) else None
    task = data.get("task_type")
    if task in {"time_series", "forecasting"} and strategy in {"random", "shuffle", "random_kfold"}:
        errors.append("time-dependent task uses a random/shuffled split")
    if fit_scope in {"all", "full", "train+validation", "global"}:
        errors.append("learned preprocessing is fitted outside the training fold/window")
    if data.get("target_derived_features"):
        errors.append("target-derived features are present without an availability-time proof")
    if not strategy:
        warnings.append("split strategy is not recorded")
    if not fit_scope:
        warnings.append("preprocessing fit scope is not recorded")
    return emit(report("leakage_check", errors, warnings, {"strategy": strategy, "fit_scope": fit_scope}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
