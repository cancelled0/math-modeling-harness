---
name: math-modeling-manager
description: 统一调度数学建模竞赛任务，在自由思路讨论、局部实验和完整提交之间选择模式；正式任务读取状态机并把一个主要动作路由给正确的专业 Skill，不替代专业分析。
---

# 数学建模总入口

把本 Skill 当作工作流入口和调度器，不当作万能求解器。专业 Skill 负责产出，`workflow-orchestrator` 负责 manifest 与阶段门，本 Skill 负责从用户意图和当前证据中选择下一条最短可靠路径。

## 模式选择

- 用户只想讨论、质疑或比较建模思路且暂不执行时，直接进入 `modeling-thought-partner`，不加载正式状态机。
- 局部实验、学习和临时分析使用 `lean`。
- 完整赛题、持续建模、正式实现或论文交付使用 `submission`，进入 `workflow-orchestrator`。

讨论模式只有在用户明确表示采用方法、开始实现、正式求解或写入方案时才退出。不要把探索性赞同解释为正式决定。

## 正式启动检查

1. 读取项目根目录 `AGENTS.md` 与 `planning/session_config.json`（若存在）。
2. 通过 `workflow-orchestrator/scripts/workflow.py` 或其 Skill 契约检查当前 Qx、profile、阶段门、阻塞项、Git 状态和允许动作。
3. 若尚无实际赛题，仅给出路由或初始化最小所需目录，不创建完整工作区。
4. 若请求是明确单项任务，直接路由专业 Skill；完成后再由 `workflow-orchestrator` 刷新状态。

## 默认决策边界

机械步骤在权限范围内自动推进，只在四类实质判断暂停：重大题意歧义、最终方法选择、结果接受/调整/备选启用、数值冻结与声明范围。通过 `decision-prompt-builder` 构造选择卡，通过 `modeler-decision-logger` 记录答案。

不要把实现细节伪装成人工判断，也不要替用户生成理由。

## 路由步骤

1. 识别请求属于新赛题、既有阶段续作、局部分析、故障恢复或论文交付。
2. 读取 [完整流程](references/workflow.md)，只定位当前阶段。
3. 从 [路由矩阵](references/routing-matrix.md) 选择一个主要 Skill。
4. 涉及算法族选择时读取 [方法情景](references/method-scenarios.md)。
5. 出现失败、退化或证据冲突时读取 [故障手册](references/failure-playbook.md)。
6. 需要机器可读查询或交接审计时读取 [Skill 注册表](references/skill-registry.json)。
7. 正式赛题的方法讨论前读取 [证据优先级](references/evidence-policy.md)，完成有边界的学术证据扫描。

只安排一个承担当前关键路径的主要 Skill。可列出少量真正独立、不会提前作出判断的并行辅助动作；不得一次投机调用多个会改变模型选择的 Skill。

## 强制交接

- 新赛题：`problem-parser` → `problem-classifier` → 学术证据/数据路径 → 可选思路讨论 → `method-selector`。
- 数据路径：有本地附件先 `data-auditor-cleaner`；缺少外部证据或数据时先 `modeling-evidence-collector`；需要衍生预测量、指标体系或变量约简时进入 `feature-engineering`。
- 代码路径：人工方法选择后 `git-experiment-manager` 建立实验上下文，再执行 `model-code-analyzer` → 语言生成器 → `code-reviewer`。
- 评估路径：`result-report-generator` 先作问题归因，再按需进入 `feature-engineering`、专业方法 Skill、代码修复或 `robustness-checker`。
- 论文路径：结果冻结后按流程生成解释、结果、图表、分节、引用和润色；中文 LaTeX 交给 `latex-paper-zh`，英文 LaTeX 交给 `latex-paper-en`，随后执行三层审计。

## 会话配置

实际赛题开始时可把 [会话配置模板](assets/session_config.template.json) 复制到 `planning/session_config.json` 并按用户要求修改。`submission` 用于完整参赛交付，`lean` 用于局部实验与学习。

## 输出

讨论模式按 `modeling-thought-partner` 自然交流。正式模式每次只报告：当前 profile、当前 Qx/阶段门、证据或阻塞项、Git 实验上下文、一个主要下一动作、需要人工确认的理由（若有）。随后执行已获授权且不需要人工判断的动作。

## 验证

修改 Skill 集或路由后运行 `scripts/audit_skill_routes.py`，并用 `evals/routing_cases.json` 检查典型情景。管理器不得越过 G2.5、G4 冻结或四类人工判断点。
