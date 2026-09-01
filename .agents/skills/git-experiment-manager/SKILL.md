---
name: git-experiment-manager
description: 用 Git 为数学建模算法实验建立稳定快照、实验分支、可比结果记录、接受合并与可恢复回退。用于用户确认要实现或更换算法之后；不在纯思路讨论中创建提交。
---

# Git 算法实验管理

把 Git 作为实验谱系而不是简单备份。读取 [版本策略](references/versioning-policy.md)，并优先使用 `scripts/experiment_git.py` 和 `scripts/compare_experiments.py` 完成确定性操作。

## 进入条件

- 用户已经明确要求实现、调整或比较算法；纯讨论不得创建分支。
- 当前方法决定或结果调整决定已记录，或者这是建立正式基线的机械提交。
- 工作区是 Git 仓库，且未归属的用户改动已识别。不要自动暂存无关文件。

## 工作流

1. 在稳定分支保存当前可复现 checkpoint。
2. 创建 `exp/<contest>/<Qx>/<algorithm>` 分支；名称冲突时增加短序号，不覆盖旧实验。
3. 实现并运行实验，把 commit、父 commit、数据/划分/特征/指标哈希、随机种子和环境写入 `run_summary.json` 与 `planning/experiment_registry.jsonl`。
4. 只有比较契约一致时运行结果对比并允许“更优/更差”的结论。
5. 人工接受后以非快进合并回稳定分支；人工拒绝时保留分支与结果记录并切回稳定分支。
6. 已合并方案需要恢复时使用 `git revert` 留下历史，不使用 `git reset --hard`。

## 规则

- 不提交密钥、原始大数据、缓存、环境目录或大型模型；用路径和哈希登记。
- 不删除被拒绝的实验分支，除非用户明确要求清理。
- 不因指标变化自动接受、拒绝或回退算法。
- 冻结后的算法变更必须先记录解冻，并让 `workflow-orchestrator` 将受影响步骤标记为 stale。

## 交接

- 分支建立后交给 `model-code-analyzer` 或被诊断出的数据/特征/实现 Skill。
- 实验完成后交给 `result-report-generator` 与 `compare_experiments.py`。
- 接受、调整或拒绝由 `decision-prompt-builder` 和 `modeler-decision-logger` 记录。
