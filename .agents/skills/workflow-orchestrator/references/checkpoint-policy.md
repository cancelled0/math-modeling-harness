# 人工检查点

四类判断都使用 `policy=never_auto_approve`：

1. `framing_choice`：只有会改变题意、输出或声明范围的歧义才触发。
2. `method_choice`：确认方法契约中的 main 与 reference policy。
3. `result_verdict`：接受、调整、拒绝或启用 fallback；稳定性判断并入此处。
4. `claim_freeze`：对冻结声明选择 accept、downgrade 或 drop。

`record-decision` 只记录用户实际给出的原话和选择，不生成理由、不把 agent 建议写成 human。决定证据哈希失效后必须重新记录；普通参数、图表和写作选择不新增检查点。
