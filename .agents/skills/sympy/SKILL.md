---
name: sympy
description: Use SymPy for exact symbolic algebra, calculus, equation solving, symbolic linear algebra, or verified expression-to-code conversion when exact manipulation is useful.
license: BSD-3-Clause
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# SymPy

先声明符号的域、假设、单位和所需解支。保留精确数直到确需数值化；方程求解后把候选解代回原式，并检查定义域、分支和奇点。

正式工作区中，SymPy 用于核验推导或生成已批准模型的表达式，不自行改变模型。数值规模较大或只需近似计算时，优先使用合适的数值工具。

需要具体代数、微积分、矩阵或代码生成模式时，读取 [详细指南](references/detailed-guide.md)。
