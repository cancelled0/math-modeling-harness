---
name: scientific-visualization
description: Provide specialist chart-design or accessibility guidance for difficult scientific figures. Contest figure planning, generation, provenance, and render verification remain owned by math-figure-generator.
license: MIT
metadata:
  compatibility: Inspect available plotting and rendering tools; example pins are optional reference environments.
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 科学图形专项支持

仅在图形编码、复杂多面板、不确定性、缺失数据、色觉可访问性或期刊导出要求需要专项判断时使用。普通数模图表由 `math-figure-generator` 直接完成，避免两个 Skill 同时维护图表清单和文件状态。

本 Skill 给出具体设计或审计建议，不另建竞争性的图表计划。正式输出仍由 `math-figure-generator` 绑定数据来源、声明和渲染结果。

需要配色、出版规范、Matplotlib 示例或现有工具脚本时，读取 [详细指南](references/detailed-guide.md) 和相应参考文件。
