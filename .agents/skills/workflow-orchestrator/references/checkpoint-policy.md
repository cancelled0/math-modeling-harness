# 人工检查点

三类判断都使用 `policy=never_auto_approve`：

三类检查点只在 pipeline 对应步骤中定义；运行器和审计器从步骤派生集合，不维护第二份清单。

1. `framing_choice`：只有会改变题意、输出或声明范围的歧义才触发。
2. `method_choice`：确认方法契约中的 main 与 reference policy。
3. `result_verdict`：接受、调整、拒绝或启用 fallback；稳定性判断并入此处。

`record-decision` 只记录用户实际给出的原话和选择，不生成理由、不把 agent 建议写成 human。决定证据哈希失效后必须重新记录；普通参数和展示形式不新增检查点。
