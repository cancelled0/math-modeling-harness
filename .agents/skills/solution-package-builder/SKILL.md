---
name: solution-package-builder
description: 汇总最终方法、结果、鲁棒性、图表和人工决定，生成唯一写作包并准备 claim_freeze。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

仅在 submission 的结果证据和结果判断通过后使用。读取 `method_contract.json`、foundations、`*_result_evidence.json`、适用 robustness、最终方法解释和当前决定；输出 `results/Qx/reports/qx_solution_package_for_writer.md` 与 `frozen_numbers.json`。冻结契约见 `workflow-orchestrator/assets/artifact-contracts.json`。

写入每个声明的真实来源文件、JSON 定位、单位、适用范围和限制；不要求图表计划先完成，也不创建第二个 package sign-off。`freeze` 检查点使用唯一 `claim_freeze` 决定，选择 `accept`、`downgrade` 或 `drop`；选择由运行器记录，不能自动批准。
