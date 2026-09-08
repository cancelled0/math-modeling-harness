---
name: scikit-learn
description: Implement or diagnose an approved scikit-learn pipeline for supervised learning, clustering, preprocessing, validation, or tuning. Do not use it to choose the final modeling family.
license: BSD-3-Clause
metadata:
  compatibility: Inspect the installed scikit-learn stack; use version pins only in an experiment environment or lock file.
  version: "1.2"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# scikit-learn

正式工作区中以批准的方法契约、数据划分和特征规格为准。所有学习型预处理、筛选和调参都必须位于训练折或训练窗口内；评价集不参与阈值、特征或超参数选择。

选择与任务匹配的验证方式，保存随机种子、折定义、指标实现和必要诊断。类不平衡、分组、时间顺序或概率校准存在时使用相应的拆分和评价策略。

需要具体估计器、Pipeline、搜索或指标用法时，读取 [详细指南](references/detailed-guide.md) 及其中相关参考。不要为匹配示例版本替换可用项目环境。
