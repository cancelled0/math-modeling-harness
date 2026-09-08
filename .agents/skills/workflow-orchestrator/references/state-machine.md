# 状态机与阶段门

运行器从当前 profile 模板展开 GLOBAL 与 Qx 节点，按依赖拓扑返回一个 READY 动作。节点只有在 `start → 产出 → finish` 后才可完成；输入、输出、上游证据或人工决定哈希改变会使节点失效。

阶段门顺序为 `G0 < G1 < G2 < G2.5 < G3 < G4 < G5 < G6`。模板可以跳过可选节点，但不得倒退 gate。

- G0：问题契约和实质歧义处理。
- G1：数据/证据就绪。
- G2：方法筛选产物。
- G2.5：用户批准的方法。
- G3：运行、代码审查和初步评价。
- G4：结果证据、结果决定以及 submission 的声明冻结。
- G5：论文和交付产物。
- G6：submission audit 与最终 QA。

`rerun` 只标记目标及传递下游为 stale；冻结产物受影响时标记 thaw_required。通过 `context` 生成的 Markdown/JSON 是可重建缓存，不是状态来源。
