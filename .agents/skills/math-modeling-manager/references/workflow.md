# 数学建模竞赛完整流程

本流程定义阶段顺序、证据门和人工判断点。`workflow-orchestrator` 是阶段状态的唯一调度者；专业 Skill 负责生成证据。

## S0 会话与赛题范围

- 读取根目录 `AGENTS.md` 和 `planning/session_config.json`。
- 完整 CUMCM 赛题使用 `submission`；局部学习、探索或单次实验使用 `lean`。
- 只初始化当前请求需要的目录。识别 Q1、Q2……，不得把不同子问的阶段混在一起。

## S1 理解、抽象与 G1

1. `problem-parser` 提取目标、对象、数据、约束、输出、子问依赖、变量与成功标准。
2. `problem-classifier` 标记每问的主要/次要任务类型，不选算法。
3. 必要时由 `symbol-table-builder` 和 `model-assumptions-builder` 建立全局符号、单位与假设。
4. 只有重大题意歧义才调用 `decision-prompt-builder` 暂停；答案由 `modeler-decision-logger` 记录。

G1 需要：解析、分类、数据清单、成功标准与必要的人类题意确认。

## S2 数据、外部证据与特征

- 有本地附件：`data-auditor-cleaner` 盘点、清洗并生成 `data_profile.json`。
- 需要外部数据、标准、统计或文献：`modeling-evidence-collector` 生成 `source_registry.json`；论文发现交给 `paper-lookup`，原文分析交给 `related-paper-analyzer`。
- 实验尚未采集：`experimental-design`；样本量问题交给 `statistical-power`。
- 需要派生变量、指标体系、滞后/空间/网络特征或变量约简：`feature-engineering`。
- 只需要受限的本地探索：`exploratory-data-analysis`，其结论仍须进入数据概况或特征审计。

外部数据下载后必须回到 `data-auditor-cleaner`；特征构造必须建立在划分契约上。原始数据始终只读。

## S3 方法筛选、风险探针与 G2/G2.5

1. `method-selector` 根据输出、约束、数据风险和评估预算给出：一个主候选、一个真正完成任务的可用基线、至多一个带触发条件的备选。
2. 参考 `method-scenarios.md` 选择方法族。专业库 Skill 可为风险探针提供有界技术检查，但不能在选择前铺开实现多个算法。
3. 主方法与基线均需通过适用的可执行性、假设、退化、敏感性和规模风险探针。
4. G2 通过后，在人工判断点使用选择卡；只有 JSONL 中出现人工 `DECIDED` 记录才通过 G2.5。
5. 完整的专业算法设计与代码计划在 G2.5 后进行； dormant fallback 不实现。

## S4 实现、实验与 G3

1. `model-code-analyzer` 读取方法决定、数据契约、适用的特征规格和基线，形成语言无关的实验契约。
2. 自动语言默认为 Python；用户指定 MATLAB/北太天元或主工程为 `.m` 时走 MATLAB。
3. 语言生成器实现并实际运行主方法与基线，保存同数据、同划分、同单位、同指标的比较证据。
4. `code-reviewer` 路由到语言审查器。审查必须覆盖语法、输入契约、方法一致性、可复现性、输出契约，以及适用的泄漏、预处理范围、特征选择、退化或可行性检查。

G3 只在主方法和基线执行成功、run summary 完整且必需检查通过后通过。

## S5 结果诊断、改进与 G4

1. `result-report-generator` 首先把问题归因到数据、特征、方法、参数、实现或指标定义。
2. 只修复被证据支持的层：
   - 数据问题 → `data-auditor-cleaner`；
   - 特征/变量问题 → `feature-engineering`；
   - 方法假设问题 → `method-selector`，必要时触发已记录备选；
   - 参数/不稳定 → 专业方法 Skill 与 `robustness-checker`；
   - 实现问题 → 语言生成器/审查器；
   - 指标问题 → 回到成功标准和方法卡确认。
3. `robustness-checker` 执行风险导向的消融、敏感性、扰动、重采样、误差和不确定性分析。
4. 有意义的一轮结果后，在人工判断点选择接受、调整或启用备选。不得仅因某指标下降就任意换算法。

这里先冻结“最终实验轮与结果判断”。`submission` 模式随后生成最终方法解释、结果分析、鲁棒性报告与写作包；经 package sign-off 后由 `solution-package-builder` 生成不可手改的 `frozen_numbers.json`，完成数值声明冻结。

## S6 论文、图表与 G5

1. `final-method-explainer` 建立权威方法解释。
2. `result-report-generator` 生成最终结果分析。
3. `figure-table-planner` 规划最小必要图表；`math-figure-generator` 生成并渲染验证，`scientific-visualization` 提供专项绘图支持。
4. `solution-package-builder` 完成写作包、声明范围确认和数值冻结。
5. `paper-section-writer` 只从写作包、冻结数字、人工决定和验证图表写作。
6. `reference-manager` 核验引用，`paper-polisher` 润色。
7. 中文 CUMCM 默认走 Word/Markdown 文档能力并渲染 PDF 核对；仅明确英文 LaTeX 才用 `latex-paper-en`。

G5 要求写作来源、冻结数字、人工确认的解释/声明范围和验证图表一致。

## S7 三层审计与 G6

按顺序执行：

1. `consistency-auditor`：数值、符号、参数、决定、文件和论文声明一致性；
2. `completeness-auditor`：submission 语义证据完整且未过期；
3. `quality-assurance-auditor`：工作流、证据、方法、论文与呈现的最终质量。

三个审计各自通过才允许最终组装。任何冻结证据的实质修改都必须记录解冻、重跑、重新冻结并做范围一致性复核。

## 状态改变原则

- `NONE`：排版、注释、草稿，不触发模型审计。
- `LOCAL`：冻结前的探索或方法卡局部更新，只复查局部。
- `CANONICAL`：单位、符号、方程、参数、官方值或图路径改变，做受影响 Qx 的一致性检查。
- `FROZEN`：影响冻结数值或论文声明，必须解冻并重跑相关链路。

