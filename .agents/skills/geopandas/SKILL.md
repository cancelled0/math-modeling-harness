---
name: geopandas
description: Handle GeoPandas vector data operations, CRS semantics, spatial joins, overlays, buffers, and vector I/O when those operations are actually required.
license: MIT
metadata:
  compatibility: Inspect the installed stack first; pinned examples are reference environments, not a reason to replace the project environment.
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# GeoPandas

先确认几何类型、坐标参考系、空间单位和预期拓扑含义。`set_crs` 只赋元数据，坐标变换使用 `to_crs`；距离和面积计算必须使用合适的投影或明确的测地方法。

正式赛题中，数据修复交给 `data-auditor-cleaner`，空间衍生量交给 `feature-engineering`，本 Skill 只提供空间操作和风险检查，不选择最终模型。优先复用现有环境；缺少依赖时先报告能力差距。

需要具体操作、I/O 或版本差异时，读取 [详细指南](references/detailed-guide.md)。
