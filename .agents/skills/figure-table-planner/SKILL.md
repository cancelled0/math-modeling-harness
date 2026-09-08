---
name: figure-table-planner
description: 根据已验证的结果证据规划支撑诊断、比较、论文结论和附录的最小图表集。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

读取 `*_result_evidence.json`、robustness、冻结声明和题目输出，生成 `methods/Qx/qx_figure_table_plan.json`，字段遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 figure-plan 契约。每项写明目的、claim、数据源、类型、必要性和缺失理由；没有必要图表时写 `items=[]` 与 `omission_reason`。不逐图请求人工决定，图表遵循已冻结的声明范围。
