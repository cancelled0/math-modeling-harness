# 正式路由

公共模式、证据、人工判断、Git 和结果交接政策统一见项目 `AGENTS.md`；完整步骤以 `workflow-orchestrator/assets/pipeline.template.json` 为准，profile 文件只保存差异，产物字段以 `artifact-contracts.json` 为准。

## 主链

`problem-framer → data/evidence（按需）→ method-selector → 一次方法决定 → git-experiment → foundations →（复杂任务才 implementation-spec）→ generator → language reviewer → run assessment →（按配置 robustness）→ result synthesis →（submission/配置要求时）一次结果决定 → modeling-results-presenter`

## 路径边界

- `problem-framer` 同时记录每问目标、输出、任务类型、数据需要、依赖和实质歧义；不再拆成两个互相漂移的解析/分类文件。
- `data-auditor-cleaner` 接受 `attached`、`external` 和 `none`，原始数据只读；`feature-engineering` 只处理衍生特征和变量约简。
- `method-selector` 给一个主方法和可选 reference policy；没有合适参考时写 `none_with_reason`。只有比较声明才要求可比参考。
- 结果评价分为 `run_assessment`（是否需要修复）和 `result_evidence`（供判断与展示）；普通成功轮次不生成重复 Markdown 报告。
- `modeling-results-presenter` 是两种 profile 的终止步骤，从当前证据派生正式求解过程与结果展示，不改写权威结果。

## 失效恢复

运行器将不变的 approved method family 留在同一分支，用新 run ID 区分参数、种子和实现重跑；数据定义、特征口径或方法结构变化才建立后继分支。`workflow.py rerun` 只标记受影响节点 stale，不删除历史。

继续中断任务时先生成 `workflow.py context --question Qx`，再以真实产物、manifest、决策 JSONL 和哈希为准。讨论模式不更新状态机。
