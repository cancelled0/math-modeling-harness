---
name: result-evaluator
description: Validate experiment outputs, classify failures, and synthesize one canonical result-evidence record before a human result decision. Use assessment and synthesis modes without generating routine prose reports.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 结果评价

机器字段统一遵循 `workflow-orchestrator/assets/artifact-contracts.json`。

## assessment 模式

代码审查后读取当前 `run_summary.json`、方法契约和真实输出，生成 `results/Qx/reports/qx_run_assessment.json`。核对运行状态、任务覆盖、必要参考角色、科学检查、输出退化和文件一致性，并把问题归为 data、feature、method、parameter、implementation 或 metric。

只有结果足以进入风险检查时使用 `status=ready_for_robustness`。发现实现错误、不可行、明显退化或不一致时使用 `status=needs_repair`，给出最小 `rerun_from`；这类机械修复不新增人工判断。

## synthesis 模式

在适用的鲁棒性证据完成后生成 `results/Qx/reports/qx_result_evidence.json`。只保存可追溯的结果、参考比较、误差/不确定性、稳健性、限制、触发器状态和来源路径，使用 `status=ready_for_decision`。

lean 未启用鲁棒性时，可根据 assessment 与现有证据直接 synthesis，并明确未执行的风险检查。submission 的 synthesis 必须引用当前鲁棒性摘要。

不要根据最优指标替用户接受方法，也不要为普通成功轮次生成 Markdown。用户明确要求完整展示时，`modeling-results-presenter` 从本证据派生视图；正式结果判断由状态机现有检查点记录。
