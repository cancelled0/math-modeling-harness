---
name: math-modeling-manager
description: 统一调度数学建模任务，在讨论、局部分析和正式提交之间选择模式，并把一个主要下一动作交给正确的专业 Skill。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。本 Skill 负责判断入口和路由，不替代专业建模分析。

## 模式

- 只讨论思路、质疑或比较方案：使用 `modeling-thought-partner`，不初始化状态、不写正式产物。
- 新赛题、继续既有求解、跨阶段请求或故障恢复：使用 `workflow-orchestrator`。
- 明确的单项分析直接调用对应专业 Skill，完成后刷新状态机。

## 正式入口

1. 读取项目 `AGENTS.md`、现有 `planning/session_config.json` 和 `workflow.py context --question Qx`；活动上下文仅是派生索引，权威文件优先。
2. 让运行器返回当前 profile、阶段门、阻塞项和唯一下一动作。
3. 按 [路由矩阵](references/routing-matrix.md) 只选择一个主要 Skill；独立且不改变方法判断的辅助工作才并行。
4. 出现失败先读 [故障手册](references/failure-playbook.md)，按数据、特征、方法、参数、实现或指标归因后再重跑。
5. 正式方法选择前按 [证据政策](references/evidence-policy.md) 做与风险匹配的有边界扫描。

问题契约由 `problem-framer` 一次完成；决策由运行器的 `record-decision` 保存。已批准的方法族进入 `git-experiment-manager`，代码审查直接按 Python/MATLAB 路由。结果先经 `result-evaluator`，按配置做鲁棒性，再按 profile 进行结果判断；所有正式求解最终都由 `modeling-results-presenter` 生成完整求解过程与结果展示。

## 验证

修改路由或 Skill 集后运行 `scripts/audit_skill_routes.py`；需要回归时运行其 `--smoke`。不要绕过 G2.5 或三类人工判断。
