---
name: simpy
description: Implement or audit an approved bounded discrete-event simulation with SimPy, including resources, events, warm-up, replications, monitoring, and reproducible outputs.
license: MIT
metadata:
  compatibility: Inspect the installed SimPy version; bundled examples are optional helpers.
  version: "1.2"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# SimPy

先明确实体、事件、资源、队列规则、随机分布、终止条件和观测量。正式工作区中只实现已批准的仿真模型，不让代码结构替代模型契约。

随机仿真保存种子策略、预热处理、独立重复、置信区间和运行诊断；单次轨迹不能作为稳定结论。无界到达、死锁、资源泄漏和监控偏差应显式检查。

需要具体事件模式、资源 API 或监控脚本时，读取 [详细指南](references/detailed-guide.md)。
