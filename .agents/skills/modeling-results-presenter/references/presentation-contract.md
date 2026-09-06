# 展示 JSON 契约

根字段：`schema_version: 1`、`status: "ready_for_review"`、`question_id`、`experiment_id`、`title`、`problem_goal`、`run_summary`（相对路径）。

内容字段如下；每项应包含具体分析，不以模板占位词填充：

| 字段 | 结构 |
|---|---|
| assumptions | 列表；每项 id、statement、basis、impact、validation；不适用时为空并填写 omissions.assumptions |
| preparation | 非空列表；每项 text、evidence_files（实际准备工作的文件路径） |
| derivations | 列表；每项 id、statement、derivation、conditions；无独立推导时为空并填写 omissions.derivations，勿虚构定理 |
| model | name、rationale、formulation、variables、constraints、alternatives，均为可阅读文本 |
| algorithm | name、steps（列表）、parameters、stopping_rule、reproducibility |
| results | 非空列表；每项 label、type、source_file、meaning；结构化结果附 source_locator、value，文件型附 source_sha256；number 必须说明 unit |
| conclusions | 非空列表；每项 text、scope、result_labels（引用结果 label）或 derivation_ids |
| diagnostics | baseline_comparison、robustness、limitations |
| evidence_files | 运行摘要、方法基础、审查、鲁棒性等实际文件路径列表 |

结果 type 默认为 number，必须有单位与有限数值。也支持 table、sequence、matrix（JSON 列表）、formula、text（字符串），均以 source_file、source_locator、value 校验原始内容。定位支持 `$`、`$.key.0` 或 JSON Pointer `/key/0`。例如路径结果可写 type=sequence、value=["A","B","C"]，解析解用 type=formula。

原始 CSV、图像或其他文件可用 type=table_file、figure、file，填写 source_file、source_sha256、label、meaning，无需伪造标量或 source_locator。脚本比较文件哈希；表格/图像内容的解释仍需实际阅读。所有路径相对赛题工作区。

脚本验证的是结构、来源和展示同步，不会证明自然语言推导正确。主代理仍需检查方程与代码是否一致、模型假设能否支持结论，并在对话中展示关键内容。
