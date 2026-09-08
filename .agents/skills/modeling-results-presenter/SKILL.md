---
name: modeling-results-presenter
description: 按用户需要从最终结果证据派生可读的数学建模求解过程和结果展示，不承担默认状态机步骤。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

输入 `method_contract.json`、foundations、`run_summary.json`、`run_assessment.json`、`result_evidence.json` 和 robustness；输出可选 `presentation.json`/`presentation.md`，所有数字绑定源文件和定位。它是派生视图，不覆盖权威结果证据，也不替用户作结果决定；用户需要正式写作时交 `final-method-explainer` 或写作 Skill。
