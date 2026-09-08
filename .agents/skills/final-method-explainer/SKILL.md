---
name: final-method-explainer
description: 从已批准的方法、模型基础、当前结果证据和鲁棒性证据生成权威的方法解释，供冻结与论文使用。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

输入 `method_contract.json`、`*_foundations.json`、当前 `run_summary.json`、`*_result_evidence.json`、适用的 robustness 和决策 JSONL。输出 `methods/Qx/qx_final_method_explanation.md`，所有数字、假设、单位、算法和限制都标注来源路径或定位。

只解释已经批准和实际执行的方案，不重新选方法、不重算数字、不把探索性结果写成结论。结果证据未达到 `ready_for_decision` 时停止并报告缺口；没有鲁棒性时明确记录未执行及原因。
