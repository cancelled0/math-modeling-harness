---
name: problem-framer
description: Build one model-neutral problem contract that combines subquestion parsing, output-driven task classification, data needs, dependencies, and material ambiguities before method selection.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 问题契约

把题目、附件清单和比赛要求整理为一个权威文件：`planning/problem_contract.json`。其机器字段以 `workflow-orchestrator/assets/artifact-contracts.json` 的 `problem-frame` 契约为准。

## 工作内容

1. 登记题目来源、附件及缺失材料。
2. 按每问提取目标、对象、输入、未知量、硬/软约束、输出、成功标准和跨问依赖。
3. 从输出与决策结构确定一个主要任务类型，可加一个有依据的次类型；不要靠题目关键词堆叠分类。
4. 区分题设事实、数据观察、候选关系和待判断假设。
5. 只把会改变输出、模型或声明范围的歧义放入 `material_ambiguities`。若非空，交给状态机现有的题意判断点；普通不确定性直接记录风险。

方法、库和算法名不进入本阶段。问题层已有符号、单位和不可违背假设可直接记录；方法诱导的假设和完整推导在方法选择后由 `model-assumptions-builder` 完成。

需要任务类型判据时读取 [分类指南](references/task-type-guide.md)。旧的 parse/classification 文件只在迁移时读取，不再作为新会话的双重权威源。
