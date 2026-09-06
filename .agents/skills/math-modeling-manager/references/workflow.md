# 数学建模竞赛完整流程

`modeling-thought-partner` 提供旁路讨论；`workflow-orchestrator` 是正式阶段状态的唯一调度者；专业 Skills 生成证据；Git 保存算法实验谱系。

公共模式、默认值、证据纪律、人工判断、Git 和交付政策统一见 [项目 AGENTS.md](../../../../AGENTS.md)。本文件只保留阶段路由；可执行步骤以当前会话的模板及 runtime-contract.md 为准。

## D0 自由思路讨论

进入 modeling-thought-partner，按项目 AGENTS.md 的模式边界讨论；需正式执行时返回当前阶段或初始化 S0。

## S0 会话、环境与 Git

- 从项目默认值和赛题配置解析 profile。
- `workflow.py init` 只创建最小 planning 状态和每问 manifest。
- 检查 Git、Python/MATLAB、LaTeX、Pandoc、字体和必要包；双交付还要检查 DOCX 渲染能力，不可用能力必须显式报告。
- Git 操作交给 git-experiment-manager。

## S1 题意理解与 G1

1. `problem-parser` 建立模型中立的问题契约。
2. `problem-classifier` 按输出与约束识别每问的主/次任务类型。
3. 必要时使用 `symbol-table-builder`、`model-assumptions-builder`。
4. 只有重大题意歧义才暂停，并由 JSONL 记录人工决定。

## S2 学术证据、数据与特征

按公共扫描政策及 [证据产物说明](evidence-policy.md) 生成资料摘要。

- `modeling-evidence-collector` 建立需求、来源注册表和每问 evidence brief。
- `paper-lookup` 负责可复现检索，`related-paper-analyzer` 读取原文并提取适用性与局限。
- 本地或外部数据由 `data-auditor-cleaner` 审计；原始数据只读。
- 派生特征、指标体系、变量选择和参数约简由 `feature-engineering` 完成，所有学习型转换只在训练折/窗口拟合。

扫描产物标注证据覆盖和缺口。

## D1 有证据支撑的思路讨论

用户需要时进入 `modeling-thought-partner`。可以读取题意、数据概况和 evidence brief，但仍不更新状态。讨论结束后由 `method-selector` 正式化，不把对话中的探索性赞同当作决定。

## S3 方法筛选与 G2/G2.5

1. `method-selector` 给出一个主候选、一个可完成真实任务的基线，以及至多一个带触发条件的备选。
2. 主方法和基线执行有界风险探针。
3. G2 通过后由用户确认最终方法；只有人类 `DECIDED` 记录才通过 G2.5。
4. dormant fallback 不提前实现。

## S4 Git 实验、实现与 G3

1. `git-experiment-manager` 按公共首次/后继实验政策准备分支与上下文。
2. `model-code-analyzer` 写语言中立实验契约。
3. Python/MATLAB 生成器实现主方法和基线，按公共代码 checkpoint → 受记录执行 → 审查 → 证据提交顺序操作。
4. `run_summary.json` 记录 commit、父 commit、数据/划分/特征/指标定义哈希、随机种子和环境。
5. `code-reviewer` 检查语法、契约、泄漏、预处理范围、特征一致性、可复现性、退化和可行性。

## S5 结果诊断、比较和 G4

1. `result-report-generator` 先归因为数据、特征、方法、参数、实现或指标问题。
2. 只修复有证据的层；算法变化进入新的或既有实验分支。
3. `compare_experiments.py` 只在同数据、划分、特征规格、指标定义和问题 ID 下判断优劣。
4. `robustness-checker` 执行任务适用的消融、敏感性、扰动、重采样、误差与不确定性分析。
5. `modeling-results-presenter` 生成并展示逐问求解过程，随后进入 result-verdict；后续 Git 操作依当前决定执行。
6. `final-method-explainer` 汇总最终方法；声明范围确认后由 `solution-package-builder` 生成写作包和 `frozen_numbers.json`。

## S6 论文、中文 LaTeX 与 G5

1. 最终方法解释、结果分析、图表计划和验证图件齐全。
2. `paper-section-writer` 只从写作包、冻结数字、人工决定和验证图表写作。
3. `reference-manager` 核验引用，`paper-polisher` 润色。
4. 中文 LaTeX 按项目交付配置交给 `latex-paper-zh`，执行构建、导出和交付检查。
5. 外部编辑同步与权威源规则见项目 AGENTS.md「工作区约束」。工具链缺失记录 unavailable。
6. 英文 LaTeX 使用 `latex-paper-en`。

## S7 三层审计与 G6

依次执行 `consistency-auditor`、`completeness-auditor`、`quality-assurance-auditor`。最终 PDF 和 DOCX 均需页面渲染检查；DOCX 还必须与当前 TeX 哈希一致。全部通过后创建 release commit/tag 并导出交付物。

## 失效与恢复

- `NONE`：排版或注释，不触发模型重跑。
- `LOCAL`：冻结前局部探索，只复查相关实验。
- `CANONICAL`：数据口径、单位、方程、参数或指标改变，标记受影响 Qx 下游 stale。
- `FROZEN`：记录解冻，重跑、重新冻结并做范围一致性审计。

恢复时由运行器重新验证当前哈希与依赖绑定；公共历史保留与回退政策见项目 AGENTS.md。
