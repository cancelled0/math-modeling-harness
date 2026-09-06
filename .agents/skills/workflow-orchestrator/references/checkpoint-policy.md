# 人工检查点政策

公共判断政策见 [项目 AGENTS.md](../../../../AGENTS.md)「自动推进与人工判断」。以下仅列模板使用的机器标识，与该处四项顺序对应：

1. `material_framing_ambiguity`
2. `final_method_choice`
3. `result_accept_adjust_or_fallback`
4. `number_freeze_and_claim_scope`

模板策略为 `never_auto_approve`。`modeler-decision-logger` 通过 record-decision 追加 JSONL，运行器检查 choice、user_message、decision_id、evidence_hashes，结果判断还检查 experiment_id；具体以 runtime-contract.md 和运行器为准，时间戳本身不能恢复失效证据。
