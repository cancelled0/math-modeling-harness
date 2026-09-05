# 展示 JSON 契约

根字段：`schema_version: 1`、`status: "ready_for_review"`、`question_id`、`experiment_id`、`title`、`problem_goal`、`run_summary`（相对路径）。

内容字段如下；每项应包含具体分析，不以模板占位词填充：

| 字段 | 结构 |
|---|---|
| assumptions | 非空列表；每项 id、statement、basis、impact、validation |
| preparation | 非空列表；每项 text、evidence_files（实际准备工作的文件路径） |
| derivations | 非空列表；每项 id、statement、derivation、conditions。纯数值模型也应解释目标函数或估计准则，而非虚构定理 |
| model | name、rationale、formulation、variables、constraints、alternatives，均为可阅读文本 |
| algorithm | name、steps（列表）、parameters、stopping_rule、reproducibility |
| results | 非空列表；每项 label、source_file、source_locator（如 $.primary_metric.value）、value、unit、meaning |
| conclusions | 非空列表；每项 text、scope、result_labels（引用结果 label）或 derivation_ids |
| diagnostics | baseline_comparison、robustness、limitations |
| evidence_files | 运行摘要、方法基础、审查、鲁棒性等实际文件路径列表 |

`source_locator` 只支持 JSON 对象键的点路径。表格或数组结果先保存带名称的 JSON 数值摘要，并保留原 CSV/图片路径于 evidence_files。所有路径相对赛题工作区，禁止链接不存在的文件。计量单位为无量纲时明确写“无量纲”。

脚本验证的是结构、来源和展示同步，不会证明自然语言推导正确。主代理仍需检查方程与代码是否一致、模型假设能否支持结论，并在对话中展示关键内容。
