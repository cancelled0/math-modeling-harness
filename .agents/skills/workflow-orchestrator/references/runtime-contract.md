# Runtime revision 3

模板、运行器和生产 Skill 共用 `assets/artifact-contracts.json`。每个 JSON 产物必须具备 `schema_version`、明确 `status`、真实来源路径和契约规定字段；省略项写理由。`workflow.py` 在 `finish` 时按输出索引执行契约检查。

## 关键产物

| 阶段 | 权威产物 | 最小语义 |
|---|---|---|
| problem-frame | `planning/problem_contract.json` | 题目来源、全局目标、每问目标/输出/类型/数据/依赖、实质歧义 |
| data-audit | `data_profile.json` + `source_registry.json` | 模式、输入、质量、每问 readiness；无数据须有理由 |
| method-screen | `method_contract.json` | main、reference_policy、rationale、task_type、required_checks |
| model-run | `run_summary.json` | primary result、方法结果、科学检查、execution receipt、环境和种子 |
| code-review | `*_review.json` | status、reviewed_run、checks、evidence_files |
| run-assessment | `*_run_assessment.json` | `ready_for_robustness` 或 `needs_repair`、归因、风险处理、证据 |
| result-synthesis | `*_result_evidence.json` | 结果、reference、鲁棒性、限制、证据 |
| claim_freeze | `frozen_numbers.json` | 声明范围、来源定位和拟冻结 claims；决定另存 JSONL |
| submission-audit | `paper/audits/submission_audit.json` | 完整性、一致性、哈希、交付和渲染证据 |
| quality-audit | `paper/qa_report.json` | 最终抽样、证据、未解决项 |

`reference_policy.role` 可为 `empirical_baseline`、`heuristic`、`historical`、`previous_policy`、`small_instance_oracle`、`analytic_check` 或 `none_with_reason`。只有比较声明要求执行可比 reference 和 comparison contract。

## 人工决定

仅保留 `framing_choice`、`method_choice`、`result_verdict` 和 `claim_freeze` 四类。决定必须由 `record-decision` 保存真实用户原话、typed choice、当前证据哈希；不在 Skill 间传递隐含批准。
