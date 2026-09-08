---
name: skforecast-recursive-direct
description: Implement or diagnose recursive/direct single-series forecasting with skforecast after that strategy has been selected. Do not use as the default router for every time-series forecasting problem.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# skforecast 单序列递归/直接预测

在正式工作区中，仅当方法契约已经选择递归或直接多步策略并允许 skforecast 实现时使用。保持时间顺序、预测起点、外生变量可用时间、回测窗口和不确定性定义与方法契约一致。

统计时序、状态空间或其他预测族应交给相应方法 Skill；本 Skill 不替代 `method-selector`，也不绕过统一代码生成、运行收据和审查流程。对独立的学习请求，可直接展示最小示例。

需要 API 用法和常见故障时，读取 [详细指南](references/detailed-guide.md)。
