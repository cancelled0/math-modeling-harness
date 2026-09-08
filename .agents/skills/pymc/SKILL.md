---
name: pymc
description: Build or diagnose an approved Bayesian model with PyMC, including priors, hierarchical structure, posterior sampling, predictive checks, and model comparison.
license: Apache-2.0
metadata:
  compatibility: Inspect the installed PyMC stack; exact versions in examples are reproducibility references, not mandatory upgrades.
  version: "1.3"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# PyMC

使用前明确似然、参数化、先验依据、层次结构、可识别性和目标推断量。正式工作区只实现已批准的贝叶斯方法，不以采样结果代替方法选择。

至少检查链混合、发散、有效样本量、后验预测与先验/参数化敏感性；诊断不通过时先处理模型几何或数据问题，不用增加采样数掩盖结构缺陷。

需要具体 API、采样器或诊断模式时，读取 [详细指南](references/detailed-guide.md)。优先适配当前环境，只有用户范围内确有必要时才建立新的锁定环境。
