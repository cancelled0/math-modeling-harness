---
name: workflow-orchestrator
description: 运行和检查数学建模工作区的文件型状态机，按子问题维护阶段门、产物、Git 实验上下文、暂停/恢复和局部重跑，并只路由一个下一动作；不替代专业建模工作。
---

# 数学建模状态机

读取项目 `AGENTS.md`。纯思路讨论由 `modeling-thought-partner` 旁路本 Skill；正式任务才进入状态机。

## 运行入口

优先使用 `scripts/workflow.py`：

```text
init      初始化最小会话和每问 manifest
status    派生当前状态，不伪造产物
next      返回一个主要下一动作
start     记录步骤开始与 Git 上下文
finish    验证新产物/人工决定并完成迁移
pause     暂停运行
resume    从现有证据恢复
rerun     将指定步骤及下游标记 stale，不删除历史
check     检查模板、检查器和当前状态
compare   调用 Git 实验的同口径比较
export    导出证据与交付物，不包含原始数据
smoke     在临时 Git 工作区运行模板驱动冒烟测试
```

完整定义见 [状态机](references/state-machine.md)、[步骤契约](references/step-contract.md) 和 [检查点政策](references/checkpoint-policy.md)。模板位于 `assets/`，运行器和测试必须读取同一模板，不在代码中维护另一条固定流程。

## 状态来源

依次使用：

1. `planning/workflow_run.json`；
2. `planning/manifests/Qx.json`；
3. `planning/artifacts.json`、真实产物和 JSONL 决策；
4. 兼容的旧产物。

仪表盘不能覆盖更新的 canonical 证据。每问独立推进，公共解析、分类和数据概况可以共享。

## 路由主链

- 新赛题：`problem-parser` → `problem-classifier`。
- submission 在方法讨论前：`modeling-evidence-collector` 完成学术证据扫描；论文原文由 `paper-lookup` 与 `related-paper-analyzer` 支持，外部数据回到 `data-auditor-cleaner`。
- 数据就绪后：可选 `modeling-thought-partner` 讨论 → `method-selector`。
- 人工方法决定后：`git-experiment-manager` → `model-code-analyzer` → 语言生成器 → `code-reviewer`。
- 有结果：`result-report-generator` 归因 → 人工接受/调整/备选 → `robustness-checker`。
- submission 冻结后：解释、写作包、图表、论文分节；中文 LaTeX 用 `latex-paper-zh`，英文 LaTeX 用 `latex-paper-en`。
- 最终按一致性、完整性、质量三个审计依次通过。

## 人工判断

只允许四类：重大题意歧义、最终方法选择、结果接受/调整/备选、数值冻结与声明范围。每个模板检查点都必须是 `never_auto_approve`；只有晚于失效时间的人类 `DECIDED` JSONL 记录才能完成步骤。

## Git 与重跑

算法改变先由 `git-experiment-manager` 建立实验分支。运行摘要必须包含 Git 与可比契约。`rerun` 不删除旧文件，而将受影响步骤标记 `stale`；新产物和新人工决定必须晚于失效时间。冻结证据受影响时标记 `thaw_required`，完成解冻、重跑、重新冻结和范围一致性审计。

## 变更影响

- `NONE`：排版、注释、非语义草稿。
- `LOCAL`：冻结前局部探索或实现。
- `CANONICAL`：数据口径、单位、符号、方程、参数、指标或正式图路径。
- `FROZEN`：影响冻结数值或论文声明。

只重跑受影响的 Qx 和下游步骤，不因多个文件变化就自动全量审计。

## 输出

正式调度只报告 profile、Qx、当前阶段门、阻塞/失效证据、Git branch/commit、一个主要下一动作及人工暂停理由。专业 Skill 负责内容，状态机只负责契约和迁移。

## 验证

- `workflow.py check` 通过；
- `workflow.py smoke` 通过；
- manifest 与真实产物一致；
- discussion 模式未进入状态机；
- 不存在超时自动批准；
- main/基线比较契约一致；
- LaTeX 工具不可用时状态是 `unavailable` 而不是成功。
