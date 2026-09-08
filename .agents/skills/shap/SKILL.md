---
name: shap
description: Explain an already validated machine-learning model with SHAP when feature attribution is needed, including explainer selection, background data, output-space checks, and attribution validation.
license: MIT
metadata:
  compatibility: Inspect installed SHAP and model-library versions; example pins are not mandatory project upgrades.
  version: "2.0"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# SHAP

仅在模型、特征语义和评价证据已经有效时使用。先明确解释对象、输出空间、背景/参考分布和局部或全局问题，再选择 explainer。

验证加和关系、输出形状、类别/多输出索引和背景敏感性。SHAP 说明模型如何使用输入，不自动证明因果，也不能凭单次排名删除变量；变量选择仍需同划分消融和稳定性证据。

需要具体 explainer、masker、图形或版本迁移时，读取 [详细指南](references/detailed-guide.md) 及相关参考文件。
