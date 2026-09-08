---
name: python-code-reviewer
description: 审查并验证已批准的 Python 建模实现、数据契约、泄漏风险和运行证据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

检查代码是否映射方法契约、输入输出、单位、划分、预处理、随机种子、异常处理、可复现运行和结果文件；使用 `workflow-orchestrator/assets/artifact-contracts.json` 的 code-review 契约输出 `code/Qx/reviews/qx_python_review.json`。

用户要求“审查/诊断”时只报告；用户要求完成求解时可自动修复语法、路径、I/O 等不改变数学含义的问题，并以新 run 重跑。方法、数据口径、指标或声明变化交回运行器，不在审查器内批准。
