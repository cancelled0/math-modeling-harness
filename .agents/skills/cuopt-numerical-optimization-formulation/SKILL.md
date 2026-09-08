---
name: cuopt-numerical-optimization-formulation
description: Formulate an already chosen LP, MILP, or QP as decisions, objective, constraints, domains, and verification checks. Use for optimization formulation, not for choosing the modeling family or a solver API.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 优化模型形式化

先确认目标、决策、参数、约束、变量域和单位。题意含糊且会改变可行域或目标时，交回现有题意判断点；其余缺口明确标注，不自行补造。

正式工作区中，本 Skill 只补充已经批准的方法契约，输出应能直接进入实现规格，不自行选择最终方法、生成整套代码或运行未批准实验。计数与不可分割量保持整数性；连续松弛必须显式标注。求解后至少检查状态、可行性和原约束残差。

需要分段线性、库存、混合、目标规划、二次目标或隐式约束等模式时，读取 [详细指南](references/detailed-guide.md)。
