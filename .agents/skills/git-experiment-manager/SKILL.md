---
name: git-experiment-manager
description: 用 Git 为数学建模算法实验建立稳定快照、实验分支、可比结果记录、接受合并与可恢复回退。用于用户确认要实现或更换算法之后；不在纯思路讨论中创建提交。
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Git 算法实验管理

把 Git 作为实验谱系而不是简单备份。读取 [版本策略](references/versioning-policy.md)，并优先使用 `scripts/experiment_git.py` 和 `scripts/compare_experiments.py` 完成确定性操作。

## 进入条件

- 用户已经明确要求实现、调整或比较算法；纯讨论不得创建分支。
- 当前方法决定或结果调整决定已记录，或者这是建立正式基线的机械提交。
- 工作区是 Git 仓库，且未归属的用户改动已识别。不要自动暂存无关文件。

## 工作流

1. 在稳定分支保存当前可复现 checkpoint。
2. 创建 `exp/<contest>/<Qx>/<algorithm>` 分支；名称冲突时增加短序号，不覆盖旧实验。
3. 实现后先 checkpoint 提交明确的代码与配置，再通过 `run` 执行实际命令，审查后 `record` 保存证据。执行器在运行前写收据、运行中保存日志；失败、超时与中断均保留状态，重试使用新实验编号/目录。
4. 只有比较契约一致时运行结果对比并允许“更优/更差”的结论。
5. 人工接受后以非快进合并回稳定分支；人工拒绝时保留分支与结果记录并切回稳定分支。
6. 已合并方案需要恢复时使用 `git revert` 留下历史，不使用 `git reset --hard`。

## 规则

提交范围、人工判断、历史保留与冻结后变更统一见项目 AGENTS.md「Git 与算法实验」和「工作区约束」。

## 交接

正式工作区的实验编号来自 workflow_run.json；start 自动写入相同编号，run/record 检查编号、结果目录、当前分支与父提交。重跑使用 `workflow.py rerun --question Qx --from-step <诊断步骤> --new-experiment`，执行层重跑会重新经过 git-experiment。先显式 checkpoint 当前实验代码、证据及工作流控制文件，再用带新编号的算法分支名和 `start --from-current --base main` 创建后继分支，保留已有决定和旧结果。继承 checkpoint 不代表接受旧方案；若要从稳定算法重新开始，应明确选择稳定代码来源并保留当前工作流记录。不得只改上下文字段来假装切换分支。

- 分支建立后交给 `model-code-analyzer` 或被诊断出的数据/特征/实现 Skill。
- 实验完成后交给 `result-report-generator` 与 `compare_experiments.py`。
- 接受、调整或拒绝由 `decision-prompt-builder` 和 `modeler-decision-logger` 记录。
