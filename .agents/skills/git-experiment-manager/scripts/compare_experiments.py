#!/usr/bin/env python3
"""Compare two modeling run summaries only when their evidence contracts match."""

from __future__ import annotations

import argparse
import json
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
        if not isinstance(value["value"], (int, float)):
            raise ValueError("primary_metric.value must be numeric")
        return value
    return None


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_contract = contract(left)
    right_contract = contract(right)
    mismatches = {
        key: {"left": left_contract[key], "right": right_contract[key]}
        for key in CONTRACT_KEYS
        if not left_contract[key] or left_contract[key] != right_contract[key]
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
    }
    if mismatches:
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
    if delta == 0:
        result["winner"] = "tie"
    elif right_metric["direction"] == "minimize":
        result["winner"] = "right" if delta < 0 else "left"
    else:
        result["winner"] = "right" if delta > 0 else "left"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = compare(load_json(args.left), load_json(args.right))
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
