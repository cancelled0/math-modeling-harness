---
name: robustness-checker
description: 针对已批准模型的主要风险执行敏感性、消融、稳定性、误差或不确定性检查，并保存机器证据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

读取当前 `run_summary.json`、`run_assessment.json`、方法/特征契约和数据；只测试 assessment 指出的高风险项，按任务类型选择少量有辨识力的检查。输出 `robustness/Qx/qx_robustness_summary.json`，遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 robustness 契约，记录覆盖范围、结果、限制、证据文件和未执行项目。

不因一次指标变好而换算法、不替用户接受或降级结果、不新增人工检查点。没有适用风险时可用带理由的空覆盖；submission 配置要求时必须引用当前结果证据。
