---
name: statistical-analysis
description: Select and justify a statistical test or inferential model family for already collected data, including assumptions, effect sizes, multiplicity, and uncertainty. Sample-size planning belongs to statistical-power; low-level model APIs belong to statsmodels or pymc.
license: MIT
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 统计分析

先从研究问题、响应类型、设计结构、配对/重复/聚类关系和估计目标选择检验或模型族，不能只按变量数量套检验名称。正式赛题中，本 Skill 提供统计方法和诊断依据，不绕过 `method-selector` 的最终方法决定。

报告估计量、效应量、区间和适用前提；p 值不是唯一结论。假设失败时优先选与数据结构匹配的稳健、置换、非参数或层次方案，并记录多重比较与缺失机制的影响。

需要检验选择、假设诊断、效应量或贝叶斯替代的细节时，读取 [详细指南](references/detailed-guide.md) 及其中相关参考。样本量问题直接转给 `statistical-power`。
