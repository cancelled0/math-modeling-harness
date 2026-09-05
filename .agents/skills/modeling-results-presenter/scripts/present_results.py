#!/usr/bin/env python3
"""Render a source-checked solution walkthrough, without inventing analysis."""
from __future__ import annotations
import argparse
import json
import math
import hashlib
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve(root, raw):
    p = (root / raw).resolve()
    p.relative_to(root.resolve())
    if not p.is_file():
        raise ValueError(f"结果或证据文件不存在: {raw}")
    return p


def locator(data, path):
    if path == "$":
        return data
    if path.startswith("/"):
        for key in path[1:].split("/"):
            key = key.replace("~1", "/").replace("~0", "~")
            data = data[int(key)] if isinstance(data, list) else data[key]
        return data
    if not path.startswith("$."):
        raise ValueError("仅支持 $.key.subkey 数值定位")
    for key in path[2:].split("."):
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


def validate(root, spec):
    for key in ("question_id", "experiment_id", "title", "problem_goal", "run_summary", "preparation", "model", "algorithm", "results", "conclusions", "diagnostics", "evidence_files"):
        if not spec.get(key):
            raise ValueError(f"展示缺少内容: {key}")
    for key in ("assumptions", "derivations"):
        if not isinstance(spec.get(key), list) or (not spec[key] and not spec.get("omissions", {}).get(key)):
            raise ValueError(f"{key} 必须为列表；不适用时填写 omissions.{key} 的具体原因")
    if spec.get("status") != "ready_for_review":
        raise ValueError("展示状态必须为 ready_for_review，不代表人工接受或冻结")
    run = load(resolve(root, spec["run_summary"]))
    if run.get("question_id") != spec["question_id"] or run.get("experiment_id") != spec["experiment_id"]:
        raise ValueError("展示与运行摘要不属于同一问/实验")
    for key, fields in {"assumptions": ("id", "statement", "basis", "impact", "validation"),
                        "preparation": ("text", "evidence_files"),
                        "derivations": ("id", "statement", "derivation", "conditions")}.items():
        for row in spec[key]:
            if not all(row.get(f) for f in fields):
                raise ValueError(f"{key} 记录不完整")
    for key, fields in {"model": ("name", "rationale", "formulation", "variables", "constraints", "alternatives"),
                        "algorithm": ("name", "steps", "parameters", "stopping_rule", "reproducibility"),
                        "diagnostics": ("baseline_comparison", "robustness", "limitations")}.items():
        if not all(spec[key].get(f) for f in fields):
            raise ValueError(f"{key} 记录不完整")
    for raw in spec["evidence_files"] + [p for row in spec["preparation"] for p in row["evidence_files"]]:
        resolve(root, raw)
    labels = set()
    for row in spec["results"]:
        if not all(row.get(k) for k in ("label", "source_file", "meaning")):
            raise ValueError("结果缺少名称、值、单位、含义或数值来源")
        if row["label"] in labels:
            raise ValueError("结果 label 重复")
        labels.add(row["label"])
        kind = row.get("type", "number")
        if kind in {"file", "figure", "table_file"}:
            source = resolve(root, row["source_file"])
            if row.get("source_sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
                raise ValueError("文件型结果缺少或不匹配 source_sha256")
            continue
        if kind not in {"number", "table", "sequence", "matrix", "formula", "text"}:
            raise ValueError(f"不支持的结果类型: {kind}")
        if not row.get("source_locator") or "value" not in row:
            raise ValueError("结构化结果需要 source_locator 和 value")
        actual = locator(load(resolve(root, row["source_file"])), row["source_locator"])
        value = row["value"]
        if kind == "number" and (not row.get("unit") or isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value)):
            raise ValueError("数值结果必须为有限数并说明单位")
        if kind in {"table", "sequence", "matrix"} and not isinstance(value, list):
            raise ValueError("表格/序列/矩阵应保存为 JSON 列表")
        if kind in {"formula", "text"} and not isinstance(value, str):
            raise ValueError("公式/文本应保存为字符串")
        if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(value, sort_keys=True, allow_nan=False):
            raise ValueError(f"展示数字与来源不一致或不是有限数值: {row['label']}")
    derivations = {row["id"] for row in spec["derivations"]}
    for row in spec["conclusions"]:
        if not row.get("text") or not row.get("scope") or not (row.get("result_labels") or row.get("derivation_ids")):
            raise ValueError("结论缺少范围及结果/推导证据")
        if not set(row.get("result_labels", [])) <= labels or not set(row.get("derivation_ids", [])) <= derivations:
            raise ValueError("结论引用不存在的结果或推导")


def render(root, spec):
    validate(root, spec)
    lines = [f"# {spec['question_id']}：{spec['title']}", "", f"实验：{spec['experiment_id']}；状态：待审阅，尚未接受或冻结。", "", spec["problem_goal"], "", "## 模型假设与准备", ""]
    for a in spec["assumptions"]:
        lines.extend([f"**{a['id']}：{a['statement']}**", "", f"依据：{a['basis']}。影响：{a['impact']}。验证：{a['validation']}。", ""])
    if not spec["assumptions"]:
        lines.extend(["额外假设不适用：" + spec["omissions"]["assumptions"], ""])
    for row in spec["preparation"]:
        links = "、".join(f"[{Path(p).name}](<{resolve(root,p).as_posix()}>)" for p in row["evidence_files"])
        lines.extend([row["text"] + "；证据：" + links, ""])
    model = spec["model"]
    lines.extend(["## 模型建立与选择依据", "", f"采用模型：{model['name']}。", "", model["rationale"], "", f"变量与单位：{model['variables']}", "", model["formulation"], "", f"约束与适用条件：{model['constraints']}", "", f"备选方法与取舍：{model['alternatives']}", "", "## 推导与中间结论", ""])
    for row in spec["derivations"]:
        lines.extend([f"### {row['id']}：{row['statement']}", "", row["derivation"], "", f"成立条件：{row['conditions']}", ""])
    if not spec["derivations"]:
        lines.extend(["独立推导不适用：" + spec["omissions"]["derivations"], ""])
    alg = spec["algorithm"]
    lines.extend(["## 算法与求解", "", alg["name"], ""])
    lines.extend(f"{i}. {text}" for i, text in enumerate(alg["steps"], 1))
    lines.extend(["", f"参数：{alg['parameters']}", "", f"停止条件：{alg['stopping_rule']}", "", f"复现方式：{alg['reproducibility']}", "", "## 求解结果与文件", ""])
    for row in spec["results"]:
        value = row.get("value", "见结果文件")
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        if len(str(value)) > 1200:
            value = str(value)[:1200] + "…（完整结果见文件）"
        lines.extend([f"- {row['label']}：{value} {row.get('unit', '')}。{row['meaning']} [结果文件](<{resolve(root,row['source_file']).as_posix()}>)（{row.get('source_locator', 'SHA256: ' + row.get('source_sha256', ''))}）", ""])
    lines.extend(["## 检验、比较与局限", ""])
    lines.extend([spec["diagnostics"][k] + "\n" for k in ("baseline_comparison", "robustness", "limitations")])
    lines.extend(["## 对本问的结论", ""])
    for row in spec["conclusions"]:
        lines.extend([row["text"], "", "适用范围：" + row["scope"], ""])
    return "\n".join(lines).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--spec", required=True)
    p.add_argument("--check", action="store_true")
    p.add_argument("--index", action="store_true")
    args = p.parse_args()
    try:
        root = args.workspace.resolve()
        path = resolve(root, args.spec)
        spec = load(path)
        text = render(root, spec)
        target = path.with_suffix(".md")
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != text:
                raise ValueError("展示稿未生成或与当前证据不一致")
        else:
            target.write_text(text, encoding="utf-8")
            if args.index:
                run = load(root / "planning/workflow_run.json")
                items = ["# 数学建模求解过程与结果展示", "", "以下报告供审阅；接受与冻结状态以决策账本为准。", ""]
                for q, iteration in run["iterations"].items():
                    report = root / f"results/{q}/experiments/{iteration}/presentation.md"
                    if report.is_file():
                        items.append(f"- [{q} 求解过程](<{report.as_posix()}>)")
                (root / "results/modeling_results.md").write_text("\n".join(items) + "\n", encoding="utf-8")
        print(json.dumps({"status": "passed", "report": str(target)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
