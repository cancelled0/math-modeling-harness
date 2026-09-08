---
name: math-figure-generator
description: 按已批准的图表计划生成真实、可追溯并经过渲染核对的数学建模图件。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

读取 `qx_figure_table_plan.json`、结果证据和冻结声明，输出 `paper/figures/qx_figure_manifest.json` 及实际图片/表格；manifest 字段遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 figures 契约。记录 claim、源文件/定位、哈希、单位、生成脚本和渲染检查。没有图时保留带理由的空清单。

只呈现已验证数字，不平滑、截断或改轴制造优势；复杂图形可参考 `scientific-visualization` 的技术指南，但图表计划、生成和证据归本 Skill。
