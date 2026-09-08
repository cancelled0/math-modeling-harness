---
name: quality-assurance-auditor
description: 在 submission audit 通过后做最终提交级抽样、质量和反虚构检查，生成一次 QA 结论。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

读取 `paper/audits/submission_audit.json`、当前 PDF/DOCX/TeX、冻结 claims、图表 manifest、引用和关键结果。抽样核对公式、数字、单位、页面、图表、引用和文件哈希，按 `workflow-orchestrator/assets/artifact-contracts.json` 的 quality-audit 契约输出 `paper/qa_report.json` 与简短 Markdown 视图。`status=passed` 仅在 `unresolved=[]` 且交付证据完整时使用。

本 Skill 不重新选方法、不修改冻结数字、不要求另一份 completeness/consistency 报告；发现问题交回相应生产 Skill 或运行器。
