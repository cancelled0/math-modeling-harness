---
name: matlab-model-code-generator
description: Generate and run minimal reproducible MATLAB or Beita Tianyuan compatible code for the human-approved main method and usable baseline, with compact experiment artifacts and a canonical run summary.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Preconditions

- G2.5 human method choice is recorded.
- `code/matlab/Qx/qx_code_plan.md` exists.
- Required cleaned data and profile exist.
- Required feature spec/audit exists when referenced by the code plan.
- The plan targets MATLAB or 北太天元.

Legacy artifacts may be read during migration but do not override the human decision.

# Workflow

1. Read the code plan, decision ledger, method card, probe conditions, data profile, and any referenced feature spec/audit.
2. Confirm scope: approved main plus usable baseline. Implement a fallback only after activation.
3. Generate conservative `.m` files under `code/matlab/Qx/`.
4. Prefer basic matrix/table operations and avoid optional toolboxes unless the plan approves them.
   - Fit learned preprocessing, feature selection, and tuning only on the training partition or chronological training window.
   - Enforce the retained variables/parameters in the approved feature spec and report mismatches.
5. Save tables, metrics, useful figures, and `run_summary.json` under `results/Qx/experiments/roundN/`.
   Include Git experiment ID, branch/parent context, data/split/feature/metric hashes and a structured primary metric.
6. Evaluate output-degeneracy and fallback-trigger metrics required by the plan.
7. Preserve the runner's mandatory log/receipt under project AGENTS.md; add `diary` diagnostics when a failure or warning needs them.
8. Read the active experiment ID from `planning/workflow_run.json` and use it in the result directory. Commit explicit `.m` and config paths with `git-experiment-manager checkpoint` BEFORE execution, then use `experiment_git.py run --experiment-id <id> --summary results/Qx/experiments/<id>/run_summary.json --code-paths <files> --inputs <files> -- <actual MATLAB/北太天元 command>`. The runner saves receipt and log. If the runtime is unavailable, report the unexecuted state explicitly.
9. Hand off to `code-reviewer`.
10. Use `git-experiment-manager record` to save receipt and reviewed evidence. Changed code requires a new checkpoint and fresh attempt; never relabel old results with a later commit.

# Script Layout

```text
code/matlab/Qx/
├── qx_code_plan.md
├── qx_baseline.m
├── qx_main.m
└── run_all.m        % only when useful
```

Do not create scripts for unapproved candidates or a duplicate README.

# Compatibility Rules

- Prefer `readtable`, `readmatrix`, `writetable`, `writematrix`, `save`, `load`, and `fullfile`.
- Use `rng(2026)` or the recorded seed.
- Use `jsonencode` when supported; otherwise write the required JSON fields deterministically.
- Avoid Live Scripts, App Designer, GUI code, Simulink, and toolbox-only functions unless explicitly approved.
- Note any 北太天元 compatibility risk in the run summary.

# Run Summary

Follow the `model-code-analyzer` contract, including approved decision ID, roles, paths, metrics, output-degeneracy evidence, fallback state, timing, seed, environment, warnings, and errors.

# Rules

- Do not change the selected mathematical method.
- Resolve modeling inputs from the data contract; raw-data access follows project AGENTS.md.
- Do not fabricate successful execution when MATLAB/北太天元 is unavailable.
- Do not learn preprocessing, lag choices, variable selection, or tuning settings from validation/test data.
- Keep only evidence-bearing intermediate outputs.
- Separate Type 1 diagnostics from paper figures.

# Verification

- Main and baseline are directly comparable and both executed when a runtime is available.
- Fallback code exists only when activated.
- Formal outputs and run summary exist.
- Compatibility, seed, inputs, warnings, and errors are recorded.
- Required concentration/degeneracy checks are saved.
- The run summary names the data profile and applicable feature spec, and feature outputs match that contract.
- Git and comparison-contract fields are complete enough for `compare_experiments.py`.
- Next handoff is `code-reviewer`.
