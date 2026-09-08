---
name: git-experiment-manager
description: 为已批准的方法族维护可恢复的 Git 实验上下文、执行收据、运行 ID 和可比证据。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。本 Skill 不替用户选方法，不在讨论模式创建分支。

## 生命周期

方法决定后建立一个 `exp/<contest>/<Qx>/<method-family>` 分支和 `active_experiment.json`。同一方法族的参数、随机种子、实现修复和重跑在该分支中使用新的 `run-<timestamp>` 目录；仅当方法结构、数据定义、特征口径或指标含义改变时创建后继分支。

每次运行仍记录代码 commit、输入/输出哈希、环境、随机种子和 `execution_receipt.json`。同一数据、划分、单位和指标定义才允许比较。失败运行保留，不覆盖历史。

用户要求完成求解时，可修复不改变数学含义的机械实现错误并用新 run 重跑；方法、数据、指标或声明改变交回运行器的人工检查点。`workflow.py rerun --new-run` 保持当前分支，`--new-branch` 标记结构变化。
