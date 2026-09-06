---
name: model-code-analyzer
description: Translate a human-approved main method and usable baseline into a minimal language-neutral implementation and experiment contract. Use after G2.5 and data readiness, before Python or MATLAB code generation.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Purpose

Define exactly what code must implement and save. Do not expand the approved experiment scope or fully plan a dormant fallback.

# Preconditions

- `methods/Qx/qx_method_card.md` and probe summary exist.
- `methods/Qx/qx_decisions.jsonl` contains a human `DECIDED` method choice.
- A usable baseline is identified.
- Cleaned data and `data_profile.json` are ready when data is required.
- `workspace/features/Qx/qx_feature_spec.json` and `qx_feature_audit.json` exist when the approved method depends on derived features, indicators, feature selection, or parameter reduction.
- Implementation target and round are known.

Read legacy candidate/decision artifacts only when the new artifacts are absent.

# Workflow

1. Read the approved choice, method card, probe conditions, data contract, applicable feature spec/audit, and experiment budget.
2. Plan only:
   - approved `main`;
   - approved `usable_baseline`;
   - shared helpers and comparison logic.
3. Record the fallback ID and trigger, but do not plan its full implementation unless the trigger is already evidenced and the human chose activation.
4. Map mathematical definitions to inputs, processing steps, intermediate evidence, outputs, and validation checks.
5. Define a directly comparable metric/output contract for main and baseline.
   - Main and baseline use the same eligible rows, split, units, target definition, and metric implementation.
   - All learned preprocessing and feature selection fit only inside the training partition/fold.
   - Record any deliberate baseline-specific feature restriction and why comparability remains valid.
6. Define the round output:

```text
results/Qx/experiments/roundN/
├── figures/
├── tables/
├── metrics/
└── run_summary.json
```

Use the actual workflow experiment ID instead of literal roundN. The runner always saves execution.log and execution_receipt.json, including unsuccessful attempts.
7. Write `code/Qx/qx_code_plan.md` for Python or `code/matlab/Qx/qx_code_plan.md` for MATLAB.
8. Hand off to the matching language generator.

# Run Summary Contract

Require:

```json
{
  "schema_version": 1,
  "question_id": "Q1",
  "status": "pending",
  "task_type": "regression",
  "evaluation_audit_file": "results/Q1/experiments/<active-id>/evaluation_audit.json",
  "round": "round1",
  "implementation_target": "python",
  "random_seed": 2026,
  "approved_decision_id": "q1_method_choice",
  "experiment_id": "Q1-M1-ROUND1",
  "git": {
    "branch": "exp/cumcm/q1/m1",
    "parent_commit": "...",
    "code_commit": null
  },
  "comparison_contract": {
    "question_id": "Q1",
    "data_hash": "...",
    "split_hash": "...",
    "feature_spec_hash": "...",
    "metric_definition_hash": "..."
  },
  "primary_metric": {"name": "rmse", "direction": "minimize", "value": null},
  "data_profile": "workspace/data/data_profile.json",
  "feature_spec": null,
  "methods": [
    {
      "method_id": "M1",
      "role": "usable_baseline",
      "script": "code/Q1/q1_baseline.py",
      "status": "success",
      "execution_time_seconds": 0,
      "input_files": [],
      "output_files": [],
      "figure_files": [],
      "metrics_summary": {},
      "warnings": [],
      "errors": []
    }
  ],
  "comparison": {},
  "fallback_trigger": {
    "fallback_id": null,
    "condition": null,
    "observed": false,
    "evidence": null
  },
  "environment": {}
}
```

# Code Plan Contents

Execution order: explicit code checkpoint → `experiment_git.py run` → code review → `record`. The runner fills execution.code_commit and execution.receipt_file. Read [scientific evidence](../workflow-orchestrator/references/scientific-evidence.md) for actual split/constraint checks; preserve review versus computed evidence distinctions.

- target language and round purpose;
- approved decision ID;
- main and baseline IDs and roles;
- input fields and units;
- data-profile and applicable feature-spec/audit paths, split contract, fit/transform scope, and leakage checks;
- per-method computation steps;
- comparable outputs and metrics;
- risk-probe conditions that implementation must monitor;
- fallback trigger evaluation;
- paths, seed, dependencies, and expected runtime;
- active Git experiment context and the comparison-contract hashes required by `git-experiment-manager`;
- named review checks expected downstream.
- evidence that dropped variables or reduced parameters match the approved feature audit; do not silently remove additional inputs in code.

# Rules

- Do not write executable model code.
- Do not add candidates or change model meaning.
- Do not plan a diagnostic reference as the official baseline.
- Do not implement a fallback before activation.
- Do not require duplicate logs beyond the execution evidence mandated by project AGENTS.md.
- Do not create a README when the code plan already provides the same instructions.
- Stop if a human choice, required parameter, input field, or comparable baseline output is missing.

# Verification

- Plan scope is exactly main plus usable baseline unless fallback activation is recorded.
- Outputs are directly comparable.
- Probe risks and fallback trigger are represented in `run_summary.json`.
- Feature transformations and selections are reproducible, split-safe, and traceable when applicable.
- Paths follow the experiment contract.
- Handoff targets the correct language generator.
- Run summary can be bound to a code commit and compared without relying on filenames alone.
