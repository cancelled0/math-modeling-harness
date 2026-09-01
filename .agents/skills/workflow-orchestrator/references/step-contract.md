# 步骤执行契约

模板中的每一步至少包含：

- `id`：稳定步骤标识；
- `skill`：负责生成证据的项目 Skill；
- `outputs`：完成所需的真实文件，可使用 `{question}` 与 `{question_lower}`；
- `artifact_key`：manifest 中的主产物键；
- `checks`：完成前的确定性检查名称；
- `gate_after`：该步有效后能够达到的最高阶段门；
- `checkpoint`：可选人工判断，必须声明 `never_auto_approve`。

步骤运行记录包含状态、开始/结束时间、输入和输出、错误、Git branch/commit 以及失效时间。专业 Skill 负责语义质量；运行器只验证契约、时效和状态迁移，不伪造专业结论。
