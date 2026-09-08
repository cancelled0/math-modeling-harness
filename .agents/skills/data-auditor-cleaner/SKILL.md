---
name: data-auditor-cleaner
description: Establish the canonical data context for a modeling task, including no-data tasks, attachment mapping, read-only raw sources, reproducible cleaning, and per-question readiness.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 数据上下文与清洗

生成唯一的 `workspace/data/data_profile.json`，字段遵循 `workflow-orchestrator/assets/artifact-contracts.json` 的 `data-audit` 契约。详细行级报告和清洗代码仅在实际发生非平凡转换时保存。

## 三种模式

- `attached`：盘点题目附件，映射到 Qx，审计字段、单位、键、时间、缺失、重复、异常和泄漏风险。
- `external`：在 attached 检查之外，核对实际使用文件与 `workspace/data/source_registry.json` 的来源、口径和哈希。
- `none`：题目不需要数据时，保留空 `input_files`，写明 `no_data_reason`、仍需验证的数学条件和每问 readiness；不伪造附件或创建空清洗文件。

## 清洗原则

原始文件只读，派生数据写入 `workspace/data_clean/`。表示归一化与带假设的删除、插补、缩尾、重编码分开记录；只有非平凡转换才保留脚本。外部数据的来源注册表由 `modeling-evidence-collector` 所有，本 Skill 只验证和引用，不创建第二份注册表。

数据概况记录实际输入、质量发现、覆盖范围、字段语义、单位、有效样本量，以及适用的缺失、类别不平衡、时间间隔、冗余和输出集中风险。不存在或不适用的项目使用带理由的省略。

衍生特征、指标体系和变量约简交给 `feature-engineering`。用户只要求一个局部分布或异常问题时可调用 `exploratory-data-analysis`，但其发现应回填本概况或特征审计，不另立正式数据源。
