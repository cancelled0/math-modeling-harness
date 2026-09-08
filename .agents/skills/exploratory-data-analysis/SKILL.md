---
name: exploratory-data-analysis
description: Perform a bounded, ad-hoc exploration of an explicitly named local dataset when the user wants patterns, anomalies, or sensitivity inspected. Canonical contest attachment mapping, cleaning, and readiness remain owned by data-auditor-cleaner.
license: MIT
metadata:
  compatibility: Inspect the current Python environment; bundled scripts are optional helpers, not an installation requirement.
  version: "1.1"
  skill-author: K-Dense Inc.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。

# 局部探索性分析

本 Skill 只回答一个有边界的探索问题，例如分布、缺失模式、异常值敏感性或局部泄漏风险。正式赛题的数据来源、清洗规则和可复用 `data_profile.json` 由 `data-auditor-cleaner` 维护；不要再生成一套竞争性的正式数据报告。

先确认文件、字段、单位和问题范围，再选择最小统计量或图形。输出可直接在对话中给出；只有需要复现或交接时才保存紧凑证据，并回填到数据概况或特征审计。

需要特殊科学格式或现有脚本时，读取 [详细指南](references/detailed-guide.md) 和其中相关格式参考；不因示例版本不同而更换项目环境。
