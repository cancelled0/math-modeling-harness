---
name: result-report-generator
description: Summarize modeling experiment evidence, compare the approved main method with a usable baseline, surface fallback triggers, and produce a decision-point or final report without creating routine per-round prose.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Purpose

Turn saved experiment artifacts into compact evidence. Do not treat ordinary successful runs as requiring a long report, and do not choose the winning method.

# Inputs

- `run_summary.json`
- method card and probe summary
- decision ledger
- saved tables, metrics, and figures
- session `rigor_profile`
- Git experiment context and comparison-contract hashes when algorithms or versions are compared

Stop if the run summary claims outputs that do not exist or if main and baseline are not comparable.
When comparing different Git experiments, stop the ranking claim if question, data, split, feature specification, or metric-definition hashes differ.

# Diagnostic Classification

Before recommending another experiment, classify the observed issue with evidence as one or more of:

- `data`: coverage, quality, definition, unit, or sampling problem;
- `feature`: representation, availability time, preprocessing, leakage, redundancy, or selection problem;
- `method`: load-bearing structural assumption or output form is unsuitable;
- `parameter`: calibration, hyperparameter, weight, or identifiability problem within an otherwise eligible family;
- `implementation`: code, solver, I/O, formula mapping, or randomness defect;
- `metric`: success criterion or comparison definition does not match the real task.

Name the checks that support or refute each plausible category. Do not use “try a more complex model” as an unclassified recommendation.

# Modes

## Ordinary lean round

- Validate the run summary and referenced artifacts.
- Return a compact evidence digest in the conversation.
- Do not save a Markdown report unless:
  - a fallback trigger fired;
  - a material anomaly or contradiction exists;
  - the human must make a proceed/adjust/fallback decision.

## Decision-point round

Save:

`results/Qx/experiments/roundN/qx_decision_report.md`

Include only:

- main vs baseline metrics;
- output-degeneracy/concentration evidence;
- assumption or feasibility warnings;
- robustness evidence already available;
- fallback trigger state;
- unresolved trade-offs.
- diagnostic category, supporting/refuting evidence, and the smallest justified recovery path.

Then invoke `decision-prompt-builder`. After the human answers, route the answer to `modeler-decision-logger`.

Route an approved adjustment to the diagnosed layer: data → `data-auditor-cleaner`; features/variable evidence → `feature-engineering`; method mismatch → `method-selector`; parameter/stability → the approved specialist plus `robustness-checker`; implementation → language generator/reviewer; metric definition → problem success criteria and method card. Method/fallback changes remain human-owned.

## Final/submission mode

Save:

`results/Qx/reports/qx_final_result_analysis.md`

Include:

- final main/baseline comparison;
- uncertainty and error;
- concentration/degeneracy interpretation;
- robustness links;
- limitations and applicable scope;
- exact source paths for numerical claims.

# Rejection and Fallback

- Archive a method only after a human `result_verdict` or `fallback_activation` decision.
- With Git experiment management, preserve rejected code and outputs on the experiment branch, append the rejection event, and return to the stable branch. Do not move or delete branch files merely to express rejection.
- Add one compact history line to `qx_method_card.md`; do not create a separate iteration log.
- Do not archive from an AI suggestion alone.

# Rules

- Do not fabricate metrics, comparisons, or interpretations.
- Separate facts from human verdicts.
- Do not create `result-report-generator_modeler_decision.md`.
- Do not repeat the full run summary; cite it and extract only decision-relevant evidence.
- Do not call a diagnostic reference a usable baseline.
- Do not generate paper prose.

# Verification

- Every reported number resolves to a saved artifact.
- Main/baseline comparison uses the same split, unit, and metric definition.
- Output concentration and fallback trigger are addressed.
- Reports are generated only at decision points or final mode.
- Poor results were classified before any method switch, tuning, or variable deletion was proposed.
- Accepted/rejected version claims resolve to experiment registry records and Git commits.
- Human verdicts are read from or appended to the canonical JSONL ledger.
