---
name: code-reviewer
description: Detect whether approved modeling code is Python or MATLAB/Beita Tianyuan and route it to the matching reviewer using the compact named-check review contract.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Workflow

1. Inspect target code extensions and the implementation target in `qx_code_plan.md`.
2. Route `.py` work to `python-code-reviewer`.
3. Route `.m` work to `matlab-code-reviewer`.
4. If both languages are intentionally present, review each separately.
5. If the language or target is ambiguous, report the exact conflict.

# Review Contract

New reviews write JSON and evaluate these named checks:

- `syntax`
- `input_contract`
- `method_alignment`
- `reproducibility`
- `output_contract`
- `feature_and_leakage` when a feature spec, learned preprocessing, time ordering, target-derived field, or variable/parameter selection is applicable

Additional checks are allowed when risk-driven. A review passes when all required applicable checks pass; no arbitrary bullet count is used.

`feature_and_leakage` verifies split-before-fit scope, forecast-time availability, use of the approved retained/dropped variables, and absence of target/time/preprocessing leakage. `output_contract` includes output degeneracy or metric degradation evidence required by the code plan.

# Rules

- Do not perform a second independent review in this router.
- Do not infer success because scripts exist.
- Do not require a Markdown review when the canonical JSON review exists.
- Read legacy Markdown reviews only for compatibility.
