---
name: python-model-code-generator
description: 按已批准的方法契约生成并运行最小可复现的 Python 建模实现，保存结果摘要和执行收据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

输入 `planning/problem_contract.json`、`method_contract.json`、foundations、数据概况和当前 Git 实验上下文。简单单文件任务可直接从契约实现；只有配置 `detailed_code_plan=true` 或任务复杂时才读取 `implementation_spec.json`。不重新选择方法。

输出当前 run 目录的 `run_summary.json` 及代码/结果文件。摘要必须遵循 `workflow-orchestrator/assets/artifact-contracts.json`，包含 main、适用 reference policy、primary result、必要科学检查、环境、种子和 receipt。比较声明才运行 reference；没有合适 reference 写 `none_with_reason`。

运行通过 `git-experiment-manager` 的执行器完成，保留 commit、输入哈希和输出哈希；完成后直接交 `python-code-reviewer`。
