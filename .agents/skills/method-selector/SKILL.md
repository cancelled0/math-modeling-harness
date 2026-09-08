---
name: method-selector
description: Propose a compact, evidence-backed main method, an applicable reference role, and at most one conditional fallback, then present the genuine method choice for human decision.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 方法筛选

输入为 `planning/problem_contract.json`、当前数据概况、按需特征审计和可用证据摘要。方法选择前不要求完整的方法假设或全局符号表；只使用问题层约束、单位和成功标准。

## 筛选

1. 从输出、硬约束、数据特征、验证标准、解释负担、时限和计算资源推导方法要求。
2. 提出一个 `main`。只有在比较声明或实际决策需要时才配置 `reference`：可为经验基线、启发式、历史方案、小规模精确解或解析校验；没有合适参考时使用 `none_with_reason`。
3. 最多保留一个数学结构确有不同、且有明确触发条件的 fallback。不要为凑数量增加候选。
4. 先做题面、数据和假设层风险审查。只有低成本探针能明显区分可用性时才运行临时 probe；需要非平凡实现时，记录待验证风险，留到人类选定方法后的正式实验。
5. 若用户没有给出会实质改变方法的偏好，直接基于题意和证据筛选；只有缺少负载型取舍时才先问一次，不默认增加“筛选前偏好”检查点。

## 输出

同时生成：

- `methods/Qx/qx_method_card.md`：供人阅读的紧凑选择面；
- `methods/Qx/probes/risk_probe_summary.json`：可为空探针列表并说明为何无需执行；
- `methods/Qx/method_contract.json`：机器权威，字段遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 method-screen 契约。

随后在对话中给出一次方法选择卡。用户答案由 `workflow-orchestrator record-decision` 记录；本 Skill 不创建 pending 文件，不替用户选择，也不补写用户理由。

专业库型 Skill 可提供已入围方法的局部可行性信息，但不能扩张候选池或绕过 G2.5。需要风险字段或方法族提示时读取 [风险探针](references/risk-probe-contract.md) 和 [方法族指南](references/method-family-guide.md)。
