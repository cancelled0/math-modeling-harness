---
name: statistical-power
description: Plan sample size, power, or minimum detectable effect before data collection. Use closed-form or simulation methods appropriate to the planned analysis; do not retrofit power to justify a completed study.
license: MIT
metadata:
  compatibility: Inspect available statistical libraries; exact example versions are optional reproducibility references.
  version: "1.0"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 样本量与功效

明确主要检验或估计目标、效应尺度、显著性水平、目标功效、分配比例、失访和设计效应。效应未知时给出有依据的合理范围，并报告敏感性曲线，不把单一猜测包装成精确样本量。

简单设计可用闭式计算；混合模型、聚类、重复测量、生存或复杂交互通常使用与计划分析一致的模拟。输出需包含假设、计算方法、随机误差和取整规则。

需要公式、模拟模板或效应量换算时，读取 [详细指南](references/detailed-guide.md) 及相关参考；实验布局交给 `experimental-design`。
