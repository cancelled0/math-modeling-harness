---
name: modeling-evidence-collector
description: 规划并采集数学建模所需的外部数据、统计公报、标准、论文和行业报告，记录可追溯来源与文件哈希。用于赛题附件不足、需要权威参数或希望以文献支持方法选择时；不负责最终方法选择。
---

# 建模证据采集

为数据与文献建立可复现的来源链。只采集解决当前 Qx 所需的证据，不做无边界搜索，也不把搜索摘要当作已验证数据。

## 前置条件

- 至少有初步题目解析、Qx 目标和缺失证据清单。
- 明确允许的时间、地区、单位、来源权威性和许可约束。
- 外部访问或下载必须处于用户授权与工具权限范围内。

## 工作流

1. 建立证据需求表：Qx、所需变量/参数/方法依据、可接受范围、首选权威来源和停止条件。
2. 对方法与机理证据按顺序检索：同方向高质量学术论文、官方资料与标准；不足时扩展到数学结构相同的邻近领域；仍不能覆盖关键证据时，才参考相似赛题公开解法并标记 `inspiration_only`。网页转载只作线索。
3. 论文发现交给 `paper-lookup`；获得原文或可读文本后放入 `workspace/papers/`，再交给 `related-paper-analyzer` 提取可迁移方法线索。
4. 外部数据逐项记录：来源网址、发布机构、标题、发布日期、覆盖时间、地区、字段与单位、许可/使用限制、下载时间、本地路径、文件哈希和任何转换说明。
5. 检查定义、时间口径、空间口径、币值/价格基期、单位和版本是否与赛题兼容。冲突时保留两者并标明优先规则，不静默拼接。
6. 把原始下载保存到 `workspace/data_raw/external/`，写入来源注册表，然后交给 `data-auditor-cleaner` 做结构和质量审计。
7. 按 Qx 生成 `workspace/evidence/Qx/evidence_brief.json`，分别记录题目自身事实、学术资料启示、适用性差异、未覆盖证据和 `inspiration_only` 线索，供思路讨论与 `method-selector` 使用。

## 规范输出

- `workspace/data/source_registry.json`
- `workspace/evidence/Qx/evidence_brief.json`

每个来源至少包含：

```json
{
  "source_id": "src-001",
  "kind": "dataset",
  "questions": ["Q1"],
  "publisher": "",
  "title": "",
  "url": "",
  "published_at": null,
  "coverage": {"time": null, "geography": null},
  "units": {},
  "license": null,
  "retrieved_at": "ISO-8601",
  "local_path": null,
  "sha256": null,
  "status": "planned",
  "notes": []
}
```

状态使用 `planned`、`retrieved`、`verified` 或 `rejected`。未下载的来源不得伪造哈希；不适用字段使用 `null` 并说明。

## 停止条件

- 已达到预先定义的覆盖标准；
- 权威来源明确不存在或访问受限，且替代来源的局限已记录；
- 继续搜索的预期价值低于比赛时间成本；
- 需要额外授权、付费访问或用户选择。

资料充分性不按固定篇数判断。至少检查是否覆盖：问题机理、方法适用条件、验证/基线、数据或参数依据；未覆盖项写入 evidence brief，不用低质量来源凑数。

## 规则

- 不虚构网址、发布日期、许可、DOI、数据字段或下载结果。
- 不把搜索结果页、摘要或二手图表当作原始数据。
- 不覆盖赛题附件；外部数据必须单独保存并说明为什么可合并。
- 不在本 Skill 内选择最终算法或直接撰写论文结论。
- 不把相似赛题解法当成学术证据，不复制其模型、代码或文字；只能作为有明确标签的启发。

## 验证与交接

- 每个实际使用的外部数据文件都有稳定来源、下载时间和哈希。
- 口径、单位、范围和许可已核对或明确标记风险。
- 论文与数据证据分别交给 `related-paper-analyzer` 和 `data-auditor-cleaner`。
- 每个正式 Qx 都有 evidence brief，或有“无需外部证据”的可审计理由。
- `method-selector` 只接收经审计的数据概况和可追溯的文献分析；需要自由讨论时先交给 `modeling-thought-partner`，讨论本身不改变证据状态。
