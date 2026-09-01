# 失败诊断与恢复手册

先分类，再修改。任何恢复都要保留失败证据、限定受影响范围，并让 `workflow-orchestrator` 更新下一动作。

| 症状 | 首要检查 | 问题类别 | 主要恢复 Skill | 返回点/人工判断 |
|---|---|---|---|---|
| 附件缺失或字段含义不明 | 题目附件清单、来源、单位、映射 | 数据 | `data-auditor-cleaner`；需外部补充时 `modeling-evidence-collector` | 数据就绪后回 G1/G2 |
| 缺失、异常或口径冲突 | 原始哈希、清洗规则、时间/地区/单位 | 数据 | `data-auditor-cleaner`、`uncertainty-and-units` | 假设性处理必要时确认 |
| 指标异常优秀或验证骤降 | 划分顺序、目标派生字段、全量拟合转换 | 特征/实现 | `feature-engineering`、语言审查器 | 修复后重跑 G3 |
| 训练好、验证差 | 容量、样本量、正则、时间漂移、基线 | 特征/参数/方法 | `feature-engineering`、`robustness-checker`、专业方法 Skill | 调整或备选需结果判断 |
| 变量看似无关 | VIF、置换、跨折稳定性、消融、领域必要性 | 特征 | `feature-engineering`，必要时 `shap` | 删除需多证据；最终影响交鲁棒性 |
| 参数不可识别或冗余 | 灵敏度、相关参数、后验/似然形状、单位 | 参数/机理 | `robustness-checker`、`pymc`、`sympy` | 约简改变机理时需重新确认方法/声明 |
| 结果随种子/划分剧烈波动 | 多种子、滚动窗、bootstrap、排名保留率 | 参数/数据 | `robustness-checker` | 接受、降级声明或启用备选 |
| 优化模型不可行 | 单位、符号、边界、硬约束、最小冲突集 | 方法/实现 | `cuopt-numerical-optimization-formulation`、代码审查器 | 修改约束含义需人工确认 |
| 求解可行但不可实施 | 操作约束、整数/容量、路径/时间窗 | 方法 | `method-selector`、`networkx` 或相应优化 Skill | 回 G2，必要时换备选 |
| 主方法不如基线 | 比较口径、代码一致性、风险探针假设 | 数据/特征/方法/实现/指标 | `result-report-generator` 先归因，再定向修复 | 接受/调整/备选人工判断 |
| 预测区间覆盖差 | 回测设计、残差结构、校准窗、漂移 | 参数/方法 | `forecasting-single-series`、`statsmodels`、`robustness-checker` | 重新校准或缩小声明 |
| 排名或综合分数集中 | 指标方向、缩放、权重、冗余、top-k 稳定性 | 特征/方法 | `feature-engineering`、`robustness-checker` | 权重含义改变需确认 |
| 论文数字与代码不一致 | 冻结值、来源定位、图表缓存 | 冻结证据 | `consistency-auditor` | 解冻→重跑→重新冻结 |
| 论文没有证据支撑 | 写作包、鲁棒性、人工声明范围、引用 | 写作/证据 | 对应生产 Skill、`modeling-evidence-collector`、`reference-manager` | 补证据或降级声明 |
| 文献目录为空 | 是否授权外部检索、检索问题是否明确 | 证据 | `paper-lookup` 经 `modeling-evidence-collector` 规划 | 原文到位后 `related-paper-analyzer` |
| 同方向学术资料不足 | 机理、适用性、验证/基线、数据/参数四类覆盖 | 证据 | `modeling-evidence-collector` 先扩展到邻近结构学术资料；仍不足才用相似赛题 `inspiration_only` | 更新 evidence brief 后再讨论/筛选 |
| 新算法效果变差 | Git 父提交、数据/划分/特征/指标哈希、实现审查 | 方法/实现/比较 | `git-experiment-manager` 保留实验分支，`result-report-generator` 归因 | 人工拒绝后返回稳定分支；不 reset |
| 实验结果无法直接比较 | 比较契约哈希、随机种子、环境与评估窗口 | 指标/实验 | `git-experiment-manager`、代码生成器 | 统一契约后重跑，不发布胜负结论 |
| LaTeX 无法编译 | xelatex/latexmk、MiKTeX 初始化、字体、模板、日志；外部二进制目录可通过 `MODELING_TEX_BIN` 注入 | 交付能力 | `latex-paper-zh` | 修复工具链或按配置切换 Word；不得伪造 PDF |
| 冻结后改变算法 | freeze、决定记录、Git 分支和受影响步骤 | 冻结证据 | `workflow-orchestrator` 标记 stale，`git-experiment-manager` 新建实验 | 解冻→重跑→重新冻结→一致性审计 |

## 六类归因判据

- 数据：输入本身、口径、覆盖或质量不满足任务。
- 特征：表示、时点、转换、变量选择或指标体系有问题。
- 方法：结构性假设或输出形式不适合任务。
- 参数：模型族合适，但校准、超参数、权重或可识别性不足。
- 实现：代码、求解器、随机性、I/O 或公式映射错误。
- 指标：成功标准或比较定义不能反映任务目标。

一次可记录多个候选原因，但必须用检查逐步排除。没有诊断证据时，不得以“换更复杂算法”作为默认恢复。
