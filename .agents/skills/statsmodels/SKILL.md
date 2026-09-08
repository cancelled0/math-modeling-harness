---
name: statsmodels
description: Implement or diagnose an approved statistical model with statsmodels when coefficient inference, residual diagnostics, GLM, mixed models, or classical time-series methods are needed.
license: BSD-3-Clause
metadata:
  compatibility: Inspect the installed statsmodels version and adapt APIs; pin only inside the experiment environment.
  version: "1.2"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# statsmodels

以批准的统计模型、数据结构和估计目标为准。明确响应分布、链接函数、相关结构、固定/随机效应、时间顺序和缺失处理；诊断应对应实际模型风险。

保存公式或设计矩阵、估计设置、收敛信息、残差/拟合诊断和不确定性。预测任务仍需独立留出或回测；显著性表不能替代样本外评价。

需要具体 API、模型类或诊断模式时，读取 [详细指南](references/detailed-guide.md) 及相关参考。检验族选择交给 `statistical-analysis`。
