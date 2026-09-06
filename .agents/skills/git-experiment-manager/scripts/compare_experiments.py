#!/usr/bin/env python3
"""Compare two modeling run summaries only when their evidence contracts match."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


CONTRACT_KEYS = (
    "question_id",
    "data_hash",
    "split_hash",
    "feature_spec_hash",
    "metric_definition_hash",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def contract(summary: dict[str, Any]) -> dict[str, Any]:
    nested = summary.get("comparison_contract")
    source = nested if isinstance(nested, dict) else summary
    return {key: source.get(key) for key in CONTRACT_KEYS}


def primary_metric(summary: dict[str, Any]) -> dict[str, Any] | None:
    value = summary.get("primary_metric")
    if isinstance(value, dict) and {"name", "value", "direction"} <= set(value):
        if value["direction"] not in {"minimize", "maximize"}:
            raise ValueError("primary_metric.direction must be minimize or maximize")
        if isinstance(value["value"], bool) or not isinstance(value["value"], (int, float)) or not math.isfinite(value["value"]):
            raise ValueError("primary_metric.value must be a finite number")
        return value
    return None


def compare(left: dict[str, Any], right: dict[str, Any], mode: str = "algorithm", min_improvement: float = 0.0) -> dict[str, Any]:
    if mode not in {"algorithm", "pipeline"} or not math.isfinite(min_improvement) or min_improvement < 0:
        raise ValueError("invalid comparison mode or minimum improvement")
    left_contract = contract(left)
    right_contract = contract(right)
    mismatches = {
        key: {"left": left_contract[key], "right": right_contract[key]}
        for key in CONTRACT_KEYS
        if (mode != "pipeline" or key != "feature_spec_hash") and (not left_contract[key] or left_contract[key] != right_contract[key])
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "left_experiment": left.get("experiment_id"),
        "right_experiment": right.get("experiment_id"),
        "comparable": not mismatches,
        "contract_mismatches": mismatches,
        "winner": None,
        "primary_metric_delta_right_minus_left": None,
        "warnings": [],
        "mode": mode,
        "acceptance": "human_required",
    }
    for name, summary in (("left", left), ("right", right)):
        if summary.get("status") not in {"PASSED", "passed", "success"} or summary.get("feasible") is False:
            result["contract_mismatches"][name + "_run_status"] = "failed, unknown, or infeasible"
        if not summary.get("execution", {}).get("code_commit"):
            result["contract_mismatches"][name + "_provenance"] = "missing executed commit"
    if mode == "pipeline":
        for key in ("target_hash", "evaluation_rows_hash", "population_hash"):
            a = left.get("comparison_contract", {}).get(key)
            b = right.get("comparison_contract", {}).get(key)
            if not a or a != b:
                result["contract_mismatches"][key] = {"left": a, "right": b}
    result["comparable"] = not result["contract_mismatches"]
    if not result["comparable"]:
        result["warnings"].append("比较契约不一致，禁止据此宣称某算法更优。")
        return result

    left_metric = primary_metric(left)
    right_metric = primary_metric(right)
    if not left_metric or not right_metric:
        result["warnings"].append("缺少结构化 primary_metric，只确认实验可比，不判定优劣。")
        return result
    if left_metric["name"] != right_metric["name"] or left_metric["direction"] != right_metric["direction"]:
        result["comparable"] = False
        result["contract_mismatches"]["primary_metric"] = {
            "left": left_metric,
            "right": right_metric,
        }
        result["warnings"].append("主指标名称或方向不一致。")
        return result

    delta = float(right_metric["value"]) - float(left_metric["value"])
    result["primary_metric_delta_right_minus_left"] = delta
    if abs(delta) <= min_improvement:
        result["winner"] = "tie"
    elif right_metric["direction"] == "minimize":
        result["winner"] = "right" if delta < 0 else "left"
    else:
        result["winner"] = "right" if delta > 0 else "left"
    result["warnings"].append("winner 仅表示当前主指标方向；接受方案还需结合不确定性、稳定性、约束和计算成本。")
    result["secondary_evidence"] = {name: {k: run.get(k) for k in ("uncertainty", "random_seed", "environment", "runtime_seconds", "scientific_checks")} for name, run in (("left", left), ("right", right))}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=("algorithm", "pipeline"), default="algorithm")
    parser.add_argument("--min-improvement", type=float, default=0.0)
    args = parser.parse_args()
    try:
        result = compare(load_json(args.left), load_json(args.right), args.mode, args.min_improvement)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["comparable"] else 2


if __name__ == "__main__":
    sys.exit(main())
