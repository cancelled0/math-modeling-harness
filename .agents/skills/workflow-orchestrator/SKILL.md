---
name: workflow-orchestrator
description: 运行和检查数学建模工作区的文件型状态机，按子问题维护阶段门、产物、Git 实验上下文、暂停/恢复和局部重跑，并只路由一个下一动作；不替代专业建模工作。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# 数学建模状态机

当前执行契约以 [Runtime revision 2](references/runtime-contract.md) 为准，正式工作先读取它。旧会话用 migrate 备份并重新验证。新增结果展示位于鲁棒性之后、结果判断之前。start/finish 执行检查并绑定依赖哈希，文件存在不会自动完成步骤。

科学验证读取 [可执行证据契约](references/scientific-evidence.md)。人工答案优先用 `record-decision` 保存原话、当前哈希与实验编号，用户未解释理由时允许为空。新实验重跑会回到 Git 上下文准备；保存 checkpoint 后建立后继分支，再实施诊断出的修复。

继续既有任务或从中断恢复时，先运行 `context` 并读取对应 Qx 的活动上下文；其缓存规则与字段见 [活动上下文索引](references/active-context.md)。索引只帮助定位，不覆盖权威产物。

读取项目 `AGENTS.md`。纯思路讨论由 `modeling-thought-partner` 旁路本 Skill；正式任务才进入状态机。

## 运行入口

优先使用 `scripts/workflow.py`：

```text
init      初始化最小会话和每问 manifest
status    派生当前状态，不伪造产物
next      返回一个主要下一动作
context   为一个或全部 Qx 生成可重建的 JSON/Markdown 活动上下文
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

常用形式：

```text
workflow.py --workspace <赛题目录> context --question Q1
workflow.py --workspace <赛题目录> context --all --format json
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
- 有结果：`result-report-generator` → `robustness-checker` → `modeling-results-presenter` → 人工结果判断。
- submission 冻结后：解释、写作包、图表、论文分节；中文默认由 `latex-paper-zh` 先构建 PDF，再从唯一 TeX 主源派生带哈希的 DOCX 镜像，英文 LaTeX 用 `latex-paper-en`。
- 最终按一致性、完整性、质量三个审计依次通过。

## 人工判断

判断范围见项目 AGENTS.md「自动推进与人工判断」。模板使用 `never_auto_approve`；运行器校验人类 DECIDED 记录及其当前证据哈希，而非仅检查记录时间。

## Git 与重跑

Git 公共政策见项目 AGENTS.md「Git 与算法实验」。`rerun` 将受影响步骤标记 stale；冻结证据受影响时标记 thaw_required。通过 start/finish 校验当前证据绑定后重新完成步骤。

## 变更影响

- `NONE`：排版、注释、非语义草稿。
- `LOCAL`：冻结前局部探索或实现。
- `CANONICAL`：数据口径、单位、符号、方程、参数、指标或正式图路径。
- `FROZEN`：影响冻结数值或论文声明。

重跑范围遵循项目 AGENTS.md「公共汇报与变更范围」。

## 输出

按项目 AGENTS.md「公共汇报与变更范围」输出调度状态。

## 验证

- `workflow.py check` 通过；
- `workflow.py smoke` 通过；
- manifest 与真实产物一致；
- discussion 模式未进入状态机；
- 不存在超时自动批准；
- main/基线比较契约一致；
- LaTeX 工具不可用时状态是 `unavailable` 而不是成功。
- 双交付模式按 `latex-build` → `docx-export` 顺序推进，DOCX 与当前 TeX 哈希不一致时不能完成 G5。
