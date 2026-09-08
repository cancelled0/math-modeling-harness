# 步骤执行契约

模板中的每一步至少包含：

- `id`：稳定步骤标识；
- `skill`：负责生成证据的项目 Skill；
- `outputs`：完成所需的真实文件，可使用 `{question}` 与 `{question_lower}`；
- `artifact_key`：manifest 中的主产物键；
- `checks`：完成前的确定性检查名称；
- `gate_after`：该步有效后能够达到的最高阶段门；
- `checkpoint`：可选人工判断，必须声明 `never_auto_approve`。
- `scope`：`global` 或每问；全局步骤只实例化一次并可等待全部 Qx。
- `depends_on` / `inputs`：显式依赖和输入，运行器对输入、输出、上游证据和人工决定计算快照。
- `checks` 中的专用契约由 Runtime revision 3 和 `assets/artifact-contracts.json` 执行；未知检查不能默默跳过。

步骤运行记录包含状态、开始/结束时间、输入和输出、证据快照、错误、Git branch/commit 以及失效时间。`result-evaluator` 先生成机器结果证据；`modeling-results-presenter` 仅在用户需要完整讲解时从该证据派生视图。专业 Skill 负责语义质量；运行器验证契约、证据、时效和状态迁移，不伪造专业结论。
