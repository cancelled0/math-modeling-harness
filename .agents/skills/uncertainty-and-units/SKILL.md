---
name: uncertainty-and-units
description: Check physical units, dimensional consistency, measurement-uncertainty propagation, or order-of-magnitude plausibility when these issues are material to a model or result.
license: MIT
metadata:
  compatibility: Static checks need no special environment; inspect available numeric libraries before using optional helpers.
  version: "1.0"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 单位与不确定性

记录量、单位、误差来源、相关性和所需覆盖水平。先做维度检查，再选择线性传播、协方差传播或蒙特卡洛；不确定性大、非线性强或存在边界时避免只用一阶近似。

正式工作区中把单位和不确定性证据写回方法、运行或鲁棒性产物，不另建竞争性的全局结论。显著数字和区间应与实际不确定性一致。

需要 Pint、uncertainties、GUM 预算、蒙特卡洛或量纲群细节时，读取 [详细指南](references/detailed-guide.md) 及相关参考。不要为示例版本强制更换项目环境。
