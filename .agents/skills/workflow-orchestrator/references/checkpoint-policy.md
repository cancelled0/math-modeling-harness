# 人工检查点政策

只允许四类会改变模型或论文声明的判断：

1. `material_framing_ambiguity`
2. `final_method_choice`
3. `result_accept_adjust_or_fallback`
4. `number_freeze_and_claim_scope`

所有检查点策略均为 `never_auto_approve`。等待时间、网络错误、任务恢复和模型建议都不能替代人工决定。决定由 `modeler-decision-logger` 追加到 JSONL；旧决定的证据失效后必须获得晚于失效时间的新记录。
