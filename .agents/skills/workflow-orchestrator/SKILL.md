---
name: workflow-orchestrator
description: 运行和检查数学建模工作区的文件型状态机，按子问题维护 manifest、阶段门、证据哈希、暂停恢复和局部重跑，并只路由一个下一动作。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)。运行器是状态唯一调度者，专业 Skill 负责实际分析与产物。

## 入口

```text
init / status / next / context / start / finish / record-decision
pause / resume / rerun / check / compare / export / reconfigure / migrate / smoke
```

完整步骤只定义在 `assets/pipeline.template.json`；`lean.template.json` 与 `cumcm-submission.template.json` 只保存 profile 差异。所有机器字段以 `assets/artifact-contracts.json` 为准。旧 revision 用 `migrate` 备份并从 `problem-frame` 重新验证。

继续任务先运行 `context --question Qx`，读取 `planning/context/Qx_active_context.md` 定位；该索引不能覆盖真实产物、manifest、决策 JSONL 或执行收据。

## 主链

`problem-frame → data/evidence → method-screen → method-choice → git-experiment → foundations → optional implementation-spec → model-run → code-review → run-assessment → optional robustness → result-synthesis → optional result-verdict → solution-presentation`

两种 profile 都以正式求解过程与结果展示结束；submission 保留更完整的学术证据、鲁棒性和结果判断要求。问题契约合并解析和分类；决策由本运行器的 `record-decision` 保存；代码审查直接按实现语言路由。

## 运行规则

- `start` 保存当前输入哈希，`finish` 验证统一契约和上游证据；文件存在不等于完成。
- `run-assessment` 为 `needs_repair` 时只按其 `rerun_from` 标记下游 stale；不替用户改变方法。
- 同一 approved method family 的参数、种子和实现重跑使用新 run ID；数据、特征、方法或指标结构改变才要求新分支。
- 人工决定必须有真实 `user_message`、typed choice、当前证据哈希；AI 建议不计入决定。
- 原始数据只读；执行必须保留 commit、环境、种子和 receipt。比较声明才强制 reference。

## 检查

运行 `workflow.py check`、`workflow.py smoke` 和管理器 `audit_skill_routes.py`。工具链 unavailable 时保留明确状态，不伪造结果、图表或数值。
