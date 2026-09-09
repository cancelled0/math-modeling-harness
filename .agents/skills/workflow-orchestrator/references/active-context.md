# 活动上下文索引

活动上下文用于在长对话压缩、任务中断、队员交接或切换小问后快速恢复当前工作。它是由状态机确定性生成的缓存，不是新的事实来源，也不能替代题意、决策账本、运行摘要或结果证据。

## 文件与命令

每问生成：

```text
planning/context/Qx_active_context.json
planning/context/Qx_active_context.md
```

命令：

```text
workflow.py --workspace <赛题目录> context --question Q1
workflow.py --workspace <赛题目录> context --all
workflow.py --workspace <赛题目录> context --question Q1 --format json
```

`status`、`next`、初始化、步骤开始/完成、人工决定、局部重跑、暂停、恢复和重新配置会刷新索引。外部文件可能在专业 Skill 执行期间改变；继续工作前运行 `context`、`status` 或 `next` 即可重建。

## 内容边界

JSON 只投影恢复工作需要的字段：

- profile、Qx、阶段门、状态和当前步骤；
- 本问目标、交付物、成功标准和约束；
- 与当前证据绑定的人工决定；
- 主方法、reference policy、备选方法；
- 数据与特征状态；
- 学术证据扫描的发现、缺口、停止原因与检索数量；
- 当前实验、运行摘要、指标和 Git 证据提交；
- 已接受或已验证的结论；
- 尚待验证的关系与模型假设；
- 失效步骤、失效决定和已拒绝实验；
- 阻塞项与一个下一动作；
- 直接权威来源的 SHA256。

不复制完整赛题、原始数据、完整结果展示、全量实验历史或自由讨论记录。过长列表和文本会机械截断并标记，不能从截断缓存反向改写权威文件。

## 真实性与确定性

- `confirmed_decisions` 只包含 `decided_by=human`、`status=DECIDED` 且仍与当前证据和依赖绑定的最新决定。
- 结果证据只有在当前结果综合有效后进入 `supported_findings`；此前放入 `hypotheses`。
- 当前有效的鲁棒性发现可进入 `supported_findings`，并保留来源路径与适用范围。
- `stale_or_rejected` 明示证据变化、步骤失效、旧决定或拒绝实验，避免恢复时误用。
- `generated.state_sha256` 由投影内容计算；`generated.as_of` 取权威记录中的最近时间，不使用每次运行的当前时间。因此同一权威状态会产生相同文件内容。
- 如果缓存与权威文件冲突，始终以权威文件为准并重新运行 `context`。

## 恢复读取顺序

1. 运行 `context --question Qx`。
2. 先读 Markdown 获取短视图；需要精确字段时读 JSON。
3. 检查 `blockers`、`stale_or_rejected` 和 `next_action`。
4. 在执行下一步前打开该动作列出的权威输入；不要只凭缓存写结论。
