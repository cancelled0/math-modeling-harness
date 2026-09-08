---
name: model-assumptions-builder
description: 在方法已批准后整理必要假设、符号、单位、准备、推导和验证计划，生成方法基础证据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

读取 `planning/problem_contract.json`、`method_contract.json`、数据概况和按需证据。输出 `methods/Qx/qx_foundations.json`，字段遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 model-foundations 契约。区分题设事实、数据观察、方法假设与待验证风险，说明假设被违反时对结果和声明的影响。

本 Skill 不重新筛选方法、不替用户批准假设；会改变题意、方法或声明范围的冲突交回既有人工检查点。
