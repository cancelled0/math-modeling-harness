---
name: modeling-results-presenter
description: 从最终结果证据生成可追溯的正式求解过程与结果展示，作为数学建模求解工作流的终止步骤。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

输入 `method_contract.json`、foundations、`run_summary.json`、`run_assessment.json`、`result_evidence.json` 和可用的 robustness 证据；输出 `results/Qx/reports/qx_solution_presentation.json` 及同名 Markdown。所有数字绑定源文件和定位。

它是求解 Harness 的正式终止产物，但仍是从权威结果证据派生的展示层，不覆盖运行摘要、结果证据或人工决定。按 [展示契约](references/presentation-contract.md) 组织模型、推导、算法、结果、检验、局限和结论，再运行 `scripts/present_results.py --workspace <workspace> --spec <presentation.json>` 生成 Markdown，并用 `--check` 验证其与当前证据一致。
