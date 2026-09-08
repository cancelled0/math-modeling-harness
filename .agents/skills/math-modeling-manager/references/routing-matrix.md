# 路由矩阵

矩阵只说明能力边界；正式步骤由当前模板和运行器返回的唯一下一动作决定。

| Skill | 触发条件 | 交付/下一步 |
|---|---|---|
| `problem-framer` | 新题目或范围变化 | `planning/problem_contract.json` → 数据/证据/方法 |
| `data-auditor-cleaner` | 附件、外部数据或无数据任务 | 数据概况/来源登记 → 特征或方法 |
| `modeling-evidence-collector` | 需要外部资料/参数依据 | evidence brief → 方法筛选 |
| `paper-lookup` / `related-paper-analyzer` | 检索或分析指定文献 | 可追溯来源/适用性 → evidence 或方法 |
| `feature-engineering` | 衍生特征、指标或约简变量 | 特征规格/审计 → 方法或重跑 |
| `method-selector` | 数据和问题契约就绪 | main + 可选 reference policy + fallback → 一次方法决定 |
| `model-assumptions-builder` / `symbol-table-builder` | 方法批准后需要基础推导 | foundations/符号单位 → 实现 |
| `git-experiment-manager` | 批准方法需要版本化运行 | method-family 分支、run ID、receipt → 生成器 |
| `model-code-analyzer` | 复杂任务要求实现计划 | implementation spec → 语言生成器 |
| `python-model-code-generator` / `matlab-model-code-generator` | 已批准方法需要执行 | run summary + 收据 → 对应 reviewer |
| `python-code-reviewer` / `matlab-code-reviewer` | 运行或实现后 | review JSON → result evaluator |
| `result-evaluator` | 运行后诊断或综合 | assessment/result evidence → robustness/决定 |
| `robustness-checker` | 结果风险需要验证 | robustness summary → result evidence |
| `modeling-results-presenter` | 用户要求完整求解展示 | 派生 presentation 视图，不改变状态 |
| `final-method-explainer` | 结果证据可供最终解释 | 方法解释 → 写作包 |
| `solution-package-builder` | submission 结果决定后 | 写作包与 claim freeze → 图表/写作 |
| `figure-table-planner` / `math-figure-generator` | 有冻结声明且图表有帮助 | 最小计划与 manifest → 写作 |
| `paper-section-writer` / `paper-polisher` | 冻结后写作或润色 | 分节 → 引用/交付 |
| `reference-manager` | 引用需要核验 | refs 与审计 → 交付 |
| `latex-paper-zh` / `latex-paper-en` | LaTeX 交付 | PDF/可选 DOCX → submission audit |
| `submission-auditor` | 交付完成 | 一次完整性/一致性审计 → QA |
| `quality-assurance-auditor` | 最终抽样质量门 | `paper/qa_report.json` |

库型 Skill 只在方法族已批准或用户明确要求时调用，不扩张候选池、不绕过运行器：`cuopt-numerical-optimization-formulation`、`geopandas`、`networkx`、`pymc`、`pymoo`、`scikit-learn`、`shap`、`simpy`、`skforecast-recursive-direct`、`statsmodels`、`sympy`、`uncertainty-and-units`、`statistical-analysis`、`statistical-power`、`experimental-design`、`scientific-visualization`、`modeling-thought-partner`、`math-modeling-manager`、`workflow-orchestrator`、`exploratory-data-analysis`。
