---
name: pymoo
description: Implement or inspect an approved multi-objective optimization model with pymoo, including constraints, termination, Pareto-set diagnostics, and reproducibility.
license: Apache-2.0
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# pymoo

先确认决策变量、目标方向、约束违反量、尺度和用户真正需要的是单一决策还是 Pareto 集。正式工作区中，本 Skill 不选择多目标方法族，只实现已批准方案。

保存随机种子、终止条件、可行率、目标尺度与解集稳定性。若需要单一推荐解，选择规则必须来自题意或已有人工判断，不能由绘图外观决定。

需要算法、问题接口、约束处理或指标细节时，读取 [详细指南](references/detailed-guide.md)。
