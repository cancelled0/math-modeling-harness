---
name: submission-auditor
description: Run one deterministic submission audit covering completeness, cross-artifact consistency, freshness, source existence, frozen claims, and rendered-delivery evidence, with scoped and final modes.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 提交审计

本 Skill 合并原 completeness 与 consistency 审计。它检查证据，不修复产物，也不重复评价论文表达质量。

## scoped 模式

仅对 `CANONICAL` 或 `FROZEN` 变更涉及的 Qx、数字、符号、参数和消费者执行检查。结果可直接在对话中返回；只有需要交接时才保存 `results/Qx/reports/scoped_submission_audit.json`。

## final 模式

检查所有提交问目，并生成：

- `paper/audits/submission_audit.json`，字段遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 submission-audit 契约；
- `paper/audits/submission_audit.md`，只作为 JSON 的简短人类视图。

至少覆盖：必需证据与适用性、哈希时效、冻结数字、公式/参数/单位、方法和参考角色、文件与引用、PDF/DOCX 当前哈希、所有页面的实际渲染检查记录。没有图、参考方法或外部数据时接受带理由的省略，不用空文件凑数。

只有全部必需检查通过且 `unresolved=[]` 时使用 `status=passed`。最终质量抽样交给 `quality-assurance-auditor`；本 Skill 不要求自己的输出或尚未生成的 QA 报告作为前置条件。
