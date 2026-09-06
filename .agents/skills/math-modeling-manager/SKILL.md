---
name: math-modeling-manager
description: 统一调度数学建模竞赛任务，在自由思路讨论、局部实验和完整提交之间选择模式；正式任务读取状态机并把一个主要动作路由给正确的专业 Skill，不替代专业分析。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# 数学建模总入口

把本 Skill 当作工作流入口和调度器，不当作万能求解器。专业 Skill 负责产出，`workflow-orchestrator` 负责 manifest 与阶段门，本 Skill 负责从用户意图和当前证据中选择下一条最短可靠路径。

## 模式选择

- 用户只想讨论、质疑或比较建模思路且暂不执行时，直接进入 `modeling-thought-partner`，不加载正式状态机。
- 执行模式和默认 profile 按项目 AGENTS.md 及当前赛题配置选择，然后进入 `workflow-orchestrator`。

讨论的授权边界与状态保持规则见项目 AGENTS.md「默认入口」及「自动推进与人工判断」。以下检查和交接用于正式执行。

## 正式启动检查

1. 读取项目根目录 `AGENTS.md` 与 `planning/session_config.json`（若存在）。
2. 通过 `workflow-orchestrator/scripts/workflow.py` 或其 Skill 契约检查当前 Qx、profile、阶段门、阻塞项、Git 状态和允许动作。
3. 若尚无实际赛题，仅给出路由或初始化最小所需目录，不创建完整工作区。
4. 若请求是明确单项任务，直接路由专业 Skill；完成后再由 `workflow-orchestrator` 刷新状态。

## 默认决策边界

按项目 AGENTS.md「自动推进与人工判断」识别判断点；需要新选择时调用 `decision-prompt-builder`，已有明确答案交给 `modeler-decision-logger`。

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
- 评估路径：`result-report-generator` 先作问题归因，再按需进入 `feature-engineering`、专业方法 Skill、代码修复或 `robustness-checker`；运行和鲁棒性证据齐全后交给 `modeling-results-presenter`，先向用户展示逐问求解过程，再进入结果判断。
- 论文路径：结果冻结后按流程生成解释、结果、图表、分节、引用和润色；中文默认由 `latex-paper-zh` 维护唯一 TeX 源、先编译 PDF、再派生并核对 DOCX 镜像，英文 LaTeX 交给 `latex-paper-en`，随后执行跨格式与三层审计。

## 会话配置

实际赛题开始时可把 [会话配置模板](assets/session_config.template.json) 复制到 `planning/session_config.json`。默认值来源为项目 AGENTS.md「默认配置」。

## 输出

按项目 AGENTS.md「公共汇报与变更范围」汇报调度状态；专业内容由当前 Skill 输出。

## 验证

修改 Skill 集或路由后运行 `scripts/audit_skill_routes.py`，并用 `evals/routing_cases.json` 检查典型情景。管理器不得越过 G2.5、G4 冻结或四类人工判断点。
