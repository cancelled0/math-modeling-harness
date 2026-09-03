# 项目 Skills 统一路由矩阵

每行给出首次使用时机、最低前置证据、主要输出和常见交接。明确的单项请求可以直接进入相应行；跨阶段请求先由 `math-modeling-manager` 与 `workflow-orchestrator` 定位。

## 调度与人工决定

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `math-modeling-manager` | 新赛题、模糊请求、跨阶段续作、失败恢复 | 用户目标或已有工作区 | 当前阶段、主要路由、必要人工点 | `workflow-orchestrator` 或一个专业 Skill |
| `modeling-thought-partner` | 只讨论、质疑或评价建模思路，暂不执行 | 用户想法及可选题意/证据摘要 | 自然追问、直接评价、替代方向；无文件产物 | 用户明确正式开始后 `math-modeling-manager` |
| `workflow-orchestrator` | 读取/更新 Qx 状态、阶段门、变更影响 | 项目规则；有赛题时有最小工作区 | manifest、门状态、一个下一动作 | 对应生产 Skill |
| `decision-prompt-builder` | 四类实质判断之一确需用户选择 | 可比较选项与证据 | 紧凑选择卡 | `modeler-decision-logger` |
| `modeler-decision-logger` | 用户已明确回答选择卡 | 原始用户答案、证据引用 | Qx/全局 JSONL 决策记录 | `workflow-orchestrator` |

## 题意理解与问题抽象

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `problem-parser` | 首次读取赛题或范围发生实质变化 | 赛题原文/附件清单 | `planning/parse/problem_parse.json` | `problem-classifier` |
| `problem-classifier` | 解析后识别每问输出结构 | problem parse | `planning/classification/problem_classification.json` | 数据/证据路径 |
| `symbol-table-builder` | 多问共享符号、单位或公式易冲突 | parse、活跃方法卡（若有） | `planning/symbol_table.md` | 方法或代码阶段 |
| `model-assumptions-builder` | 需要维护全局与方法特定假设 | parse、数据概况、方法卡 | `planning/model_assumptions.md` | `method-selector`/鲁棒性 |

## 数据、文献、实验与特征

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `modeling-evidence-collector` | submission 方法讨论前的学术扫描，或附件不足需外部数据/标准/论文 | parse、classification、Qx 证据缺口 | source registry、`workspace/evidence/Qx/evidence_brief.json` | 可选思路讨论；数据审计/论文分析/方法筛选 |
| `paper-lookup` | 需要检索论文、DOI、元数据或开放全文 | 明确检索问题 | 可复现检索结果与原文线索 | `related-paper-analyzer` |
| `related-paper-analyzer` | 已有论文原文/可读文本，需要提取方法启示 | parse、classification、`workspace/papers/` 原文 | `workspace/papers/related_paper_analysis.md` | `method-selector` |
| `data-auditor-cleaner` | 有赛题附件或新增外部数据，需要盘点、清洗与就绪判断 | parse、只读原始数据 | data report/profile、清洗数据 | `feature-engineering` 或 `method-selector` |
| `exploratory-data-analysis` | 需要受限本地 EDA 以确认数据模式/质量 | 明确支持的数据文件 | 可复现局部剖析证据 | 合并回数据概况/特征审计 |
| `feature-engineering` | 需要派生特征、指标体系、变量筛选或参数约简 | data profile、划分契约 | feature spec 与 audit JSON | `method-selector`/`model-code-analyzer`/`robustness-checker` |
| `experimental-design` | 数据尚未采集，需要随机化、区组或处理组合 | 研究目标与可控因素 | 可执行实验设计 | 数据采集/`data-auditor-cleaner` |
| `statistical-power` | 设计样本量、功效或最小可检测效应 | 检验/效应假设、显著性与功效目标 | 功效与样本量证据 | `experimental-design` |
| `uncertainty-and-units` | 单位换算、维度检查、测量不确定性传播 | 变量、单位和误差来源 | 单位/不确定性预算与检查 | 方法、代码或鲁棒性阶段 |

## 方法筛选与专业方法能力

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `method-selector` | G1 与数据就绪后构造主方法、可用基线和条件备选 | parse、classification、data profile、必要特征/文献 | 方法卡、风险探针、方法选择卡 | 人工选择后 `model-code-analyzer` |
| `cuopt-numerical-optimization-formulation` | 已确认 LP/MILP/QP 方法族，需要变量、约束和目标形式化 | 约束、单位、方法卡 | 优化模型契约 | `model-code-analyzer` |
| `forecasting-single-series` | 已确认单序列预测，需要回测、基线与区间设计 | 时间索引、频率、预测期、划分 | 预测实现/诊断契约与运行证据 | `code-reviewer`/`robustness-checker` |
| `statistical-analysis` | 需要选检验、效应量、假设检查或统计报告 | 明确研究问题和数据结构 | 检验方案与解释证据 | `statsmodels`/代码阶段 |
| `statsmodels` | 需要 OLS/GLM/混合/ARIMA 等模型及严格诊断 | 数据、统计模型契约 | 拟合、残差与推断证据 | 代码审查/鲁棒性 |
| `scikit-learn` | 机器学习、聚类、流水线、交叉验证与调参 | 划分契约、特征规格 | 可复现 ML 流水线与评估 | `shap`（验证后）/代码审查 |
| `shap` | 已验证模型需要局部/全局归因和解释审计 | 已验证模型、背景集、特征定义 | SHAP 归因与限制 | `robustness-checker`/论文图表 |
| `pymc` | 贝叶斯、层次模型、后验预测或不确定性 | 似然、先验依据、可识别参数 | 后验诊断与预测证据 | `robustness-checker` |
| `pymoo` | 多目标优化与 Pareto 前沿 | 目标、约束、变量边界、基线 | Pareto 解集与稳定性证据 | 结果判断/鲁棒性 |
| `networkx` | 图结构、路径、流、匹配或网络指标 | 节点边定义、权重、业务约束 | 图算法结果/网络特征 | 代码审查/鲁棒性 |
| `simpy` | 排队、资源、事件驱动的离散仿真 | 流程逻辑、分布、资源与终止规则 | 多重复仿真证据 | `robustness-checker` |
| `geopandas` | 矢量空间数据、空间连接、缓冲或区域统计 | 几何字段、CRS、空间任务 | 空间数据/特征与审计 | `feature-engineering`/代码阶段 |
| `sympy` | 精确代数、微积分、方程推导或符号转代码 | 数学表达与符号定义 | 可核验推导/表达式 | `model-code-analyzer` |

## 代码规划、执行与审查

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `model-code-analyzer` | G2.5 后把方法转成实验契约 | 人工方法决定、方法卡、数据契约、适用特征规格、基线 | Qx code plan | 语言生成器 |
| `git-experiment-manager` | 用户确认实现或改变算法，需要稳定快照、实验分支、比较、接受或恢复 | Git 仓库、明确实验范围、无未归属改动 | active experiment、commit 绑定、experiment registry | code plan/结果报告/稳定分支 |
| `python-model-code-generator` | code plan 目标为 Python | Python code plan 与输入 | 可运行 `.py`、结果目录、run summary | `code-reviewer` |
| `matlab-model-code-generator` | code plan 目标为 MATLAB/北太天元 | MATLAB code plan 与输入 | 可运行 `.m`、结果目录、run summary | `code-reviewer` |
| `code-reviewer` | 模型代码生成或修改后 | code plan、代码、run summary | 语言路由 | Python/MATLAB 审查器 |
| `python-code-reviewer` | Python 模型代码需要运行、修复或验证 | `.py`、方法/数据/特征契约 | `qx_python_review.json` | `result-report-generator` |
| `matlab-code-reviewer` | MATLAB/北太天元代码需要运行、兼容性或结果验证 | `.m`、运行时、方法/数据/特征契约 | `qx_matlab_review.json` | `result-report-generator` |

## 结果评估、解释与改进

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `result-report-generator` | 有意义的实验轮、异常或最终结果需要判断 | run summary、方法卡、决定、可比基线 | 诊断分类、选择卡或最终结果分析 | 定向修复/`robustness-checker` |
| `robustness-checker` | 主方法/基线已运行，需要敏感性、消融、稳定性和误差检查 | 结果、方法风险、待验证声明 | robustness summary/report | 结果判断或写作包 |
| `final-method-explainer` | submission 的最终实验轮已接受 | 最终方法、代码、假设、符号与决定 | `qx_final_method_explanation.md` | 写作包/论文 |

## 图表、论文与冻结

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `figure-table-planner` | 需要最小诊断/比较/论文图表集合 | 已验证结果与声明 | figure/table plan | 图表生成器 |
| `math-figure-generator` | 已批准图表计划，需要生成与渲染核对 | 数据源、claim、图表类型 | 实验或论文图件 | `consistency-auditor`/写作 |
| `scientific-visualization` | 需要 Matplotlib/Seaborn/Plotly 专项设计或可访问性审计 | 可信数据和图表目的 | 可复现科学图与视觉审计 | 图表计划/论文 |
| `solution-package-builder` | 最终解释、结果、鲁棒性和图表齐全，需要签署并冻结数值 | submission、人工结果/稳定性/声明决定 | writer package、`frozen_numbers.json` | `paper-section-writer` |
| `paper-section-writer` | 写作包与冻结值齐全，需要分节写中文/Markdown/TeX | G4、冻结数字、人工解释、验证图 | `paper/sections/*` | 引用核验/润色 |
| `reference-manager` | 草稿含引用或需要可追溯参考文献 | 论文草稿、论文原文/元数据 | `paper/refs.bib`、reference audit | `paper-polisher` |
| `paper-polisher` | 内容证据已定，需要语言、公式、限定语与格式润色 | 分节草稿、冻结值、符号表 | 润色后的论文节 | 最终审计 |
| `latex-paper-zh` | 中文 CUMCM TeX 组装、PDF 编译，或从当前 TeX 派生可追溯 DOCX 镜像 | G4、中文 tex 分节、引用、验证图表、LaTeX 能力；双交付另需 Pandoc | `paper/main.tex`、PDF、`paper/exports/main.docx`、构建/导出/交付报告 | `consistency-auditor` |
| `latex-paper-en` | 用户明确要求英文 LaTeX 论文/现有 `.tex` | 英文 `.tex`、目标模板与文献 | 编译通过的英文 LaTeX 稿 | 最终审计 |

中文 CUMCM 默认使用 `latex-paper-zh` 的 LaTeX 主源 + DOCX 镜像路径；显式 Word 主格式仍是配置备选。PDF 页面渲染与 DOCX 文档渲染继续使用当前环境能力，它们不是本项目 `.agents/skills` 注册表中的项目 Skill。

## 最终审计

| Skill | 何时使用 | 最低前置条件 | 主要输出 | 常见下一步 |
|---|---|---|---|---|
| `consistency-auditor` | canonical/frozen 变更后的范围核对，或最终跨媒体核对 | 来源与消费者清单 | scoped JSON 或最终一致性报告 | 修复/`completeness-auditor` |
| `completeness-auditor` | 检查当前 profile 的语义证据是否齐全、当前 | manifests 与应有产物 | completeness audit | 修复/`quality-assurance-auditor` |
| `quality-assurance-auditor` | submission 最终质量门 | G5、前两审计通过 | `paper/qa_report.md` | 最终组装或返修 |
