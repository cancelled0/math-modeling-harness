# 数学建模运行状态机

每个 Qx 独立推进；全局题意解析、分类和数据概况可以被多个 Qx 引用。运行器读取 `assets/*.template.json`，不在代码里复制另一套步骤顺序。

## 阶段门

- G0：会话、环境和最小状态已初始化。
- G1：题意、分类、数据清单、成功标准和必要证据路径明确。
- G2：主候选、可用基线、风险探针和备选触发条件形成。
- G2.5：人工方法决定有效。
- G3：实验上下文、代码计划、主方法与基线运行及代码审查通过。
- G4：结果决定、鲁棒性、写作包和冻结数字有效。
- G5：论文分节、引用、图表及选定交付格式准备完成。
- G6：一致性、完整性和最终质量审计通过。

`modeling-thought-partner` 是旁路讨论模式，不是阶段门，也不产生 manifest 状态。

## 运行状态

`pending`、`ready`、`running`、`waiting_human`、`blocked`、`completed`、`failed`、`stale`。

人工政策见 [项目 AGENTS.md](../../../../AGENTS.md)；运行器核验人类 JSONL DECIDED 记录与当前证据绑定。

## 失效与重跑

`rerun --from-step` 将该步及下游标记 stale；新实验可能先返回 git-experiment 准备上下文。重新完成时通过 start/finish 检查当前输入、输出、决定与依赖哈希，公共重跑和冻结政策见项目 AGENTS.md。

任务中断或上下文压缩后，先重建 [活动上下文索引](active-context.md)，再从其中唯一的 `next_action` 恢复；索引显示的失效、拒绝或假设内容不得当作当前结论。
