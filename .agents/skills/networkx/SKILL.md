---
name: networkx
description: Implement or inspect graph algorithms and network measures with NetworkX after nodes, edges, direction, weights, and the graph task are defined.
license: BSD-3-Clause
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# NetworkX

先明确图是有向还是无向、是否多重、权重含义、节点/边标识和任务目标。算法前置条件不满足时直接报告，例如负权与 Dijkstra、非连通图与全局指标、容量与距离混用。

正式工作区中，本 Skill 实现已批准的图模型或生成图特征；模型选择、统一运行和审查仍走主流程。大图超出内存或 NetworkX 性能范围时，先量化规模再建议替代实现。

需要算法、I/O、性能或绘图细节时，读取 [详细指南](references/detailed-guide.md)。

