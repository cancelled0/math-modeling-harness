---
name: workflow-orchestrator
description: Inspect a mathematical-modeling workspace, evaluate lean or submission gates per subquestion, update machine-readable manifests, classify change impact, and route one next action without duplicating downstream work.
---

# Purpose

Act as the gate-driven scheduler and state reader. Do not solve models, write model code, or draft paper sections.

`../../../AGENTS.md` is the project policy source relative to this `SKILL.md`. Read it before orchestration. If this Skill is copied elsewhere and that path is absent, locate the nearest ancestor `AGENTS.md`; report the missing policy rather than following the old `../../AGENTS.md` path.

# Session Start

Before orchestration in a new workspace:

- show `git status --short`;
- check the chosen runtime and required core packages;
- verify the workspace skeleton needed for the current request;
- read `planning/session_config.json`, accepting legacy `mode`.

Report warnings concisely. Do not create the full project skeleton unless the user is initializing a project.

# State Sources

Prefer, in order:

1. `planning/manifests/Qx.json`
2. canonical artifacts on disk
3. legacy dashboard and legacy method/decision artifacts

Never trust a dashboard over newer canonical artifacts.

# Manifest Contract

Maintain one compact JSON manifest per subquestion:

```json
{
  "schema_version": 1,
  "question_id": "Q1",
  "rigor_profile": "lean",
  "current_gate": "G2",
  "status": "method_screened_waiting_human",
  "artifacts": {
    "source_registry": null,
    "data_profile": "workspace/data/data_profile.json",
    "feature_spec": null,
    "feature_audit": null,
    "literature_analysis": null,
    "method_card": "methods/Q1/q1_method_card.md",
    "decision_ledger": "methods/Q1/q1_decisions.jsonl",
    "risk_probe": "methods/Q1/probes/risk_probe_summary.json",
    "latest_run": null,
    "robustness_summary": null,
    "frozen_numbers": null
  },
  "allowed": {
    "code_generation": false,
    "freeze": false,
    "paper_writing": false,
    "final_assembly": false
  },
  "blockers": [],
  "next_action": {
    "owner": "human",
    "skill": "decision-prompt-builder",
    "reason": "method choice not recorded"
  },
  "updated_at": "ISO-8601"
}
```

Update only fields affected by the current state change. Generate a human dashboard on request or at a milestone; otherwise derive status directly from manifests.

The added artifact keys are optional and do not change `schema_version`. Preserve older manifests and add a key only when the corresponding artifact is relevant or exists.

# Gate Evaluation

Evaluate each Qx independently.

## G1 — PROBLEM_FRAMED

Pass when parse, classification, data inventory, success criteria, and human framing exist. A placeholder in a human-owned field blocks the gate.

## G2 — METHOD_SCREENED

Pass when:

- `qx_method_card.md` defines a main candidate and usable baseline;
- the baseline completes the real task with comparable output;
- `risk_probe_summary.json` covers applicable checks, including output degeneracy;
- main and baseline verdicts are `PASS` or justified `CONDITIONAL`;
- any fallback has a concrete trigger.

Do not require a fixed number of candidates, universal PoCs, or a source-line limit.

## G2.5 — METHOD_CHOSEN_BY_HUMAN

Pass when `qx_decisions.jsonl` contains a human `DECIDED` method choice citing probe evidence. While blocked, allow data preparation but not model code generation.

## G3 — CODE_AND_EXPERIMENT_REVIEWED

Pass when:

- approved main and baseline executed;
- latest `run_summary.json` is complete;
- language review contains passing named checks for syntax, input contract, method alignment, reproducibility, and output contract.

Accept legacy Markdown review artifacts during migration, but prefer JSON for new work.

## G4 — RESULTS_JUDGED_AND_FROZEN

In `lean`, pass the result-judgment subgate when final-result and stability decisions cite computed evidence. Continue iterating without freezing when the human selects `adjust` or `fallback`.

In `submission`, additionally require:

- final method explanation;
- final result analysis;
- robustness report;
- package sign-off in the decision ledger;
- solution package;
- current `frozen_numbers.json`.

## G5 — PAPER_SECTION_READY

Require the three writer rules, frozen-number sourcing, human-confirmed interpretation/claim scope, and verified figures.

## G6 — FINAL_AUDIT_PASSED

Evaluate only in `submission`. Require passing consistency, completeness, and QA artifacts. Never infer that one auditor covers another.

# Routing

Choose one primary next action:

- missing framing → parser/classifier or human framing card;
- missing external data, standard, statistical bulletin, or literature source → `modeling-evidence-collector`;
- external data retrieved but not audited, or missing local data profile → `data-auditor-cleaner`;
- data ready but derived predictors, indicators, lag/spatial/network features, or evidence-backed variable reduction is required → `feature-engineering`;
- literature requested with no local originals → `modeling-evidence-collector` then `paper-lookup`;
- local paper originals available but unanalyzed → `related-paper-analyzer`;
- missing method card/probe → `method-selector`;
- missing human method choice → `decision-prompt-builder`;
- approved method without implementation plan → `model-code-analyzer`;
- code/review incomplete → language generator or reviewer;
- meaningful experiment, degraded metric, or main/baseline anomaly awaiting diagnosis → `result-report-generator`;
- diagnosed data/feature/method/parameter/implementation/metric issue → the named producer or reviewer for that layer; do not switch algorithms speculatively;
- final results without robustness → `robustness-checker`;
- submission package incomplete → final explainer, result report, or package builder;
- frozen package without a paper section → `paper-section-writer`;
- Chinese CUMCM document/PDF formatting request → document creation/editing and PDF render verification capabilities after frozen-number prerequisites;
- explicit English LaTeX request → `latex-paper-en`;
- paper ready but unaudited → the earliest missing final auditor: consistency, then completeness, then QA.

Do not invoke several judgment-bearing skills speculatively.

# Change Impact

Classify changes before scheduling checks:

- `NONE`: scratch, formatting, comments, non-semantic docs.
- `LOCAL`: exploratory code or method-card updates before freeze.
- `CANONICAL`: schema/units, symbols, equations, parameters, official values, figure paths.
- `FROZEN`: changes affecting frozen values or paper claims.

Route checks:

- `NONE`: none.
- `LOCAL`: local tests/review.
- `CANONICAL`: scoped consistency for affected Qx.
- `FROZEN`: thaw log, rerun affected work, re-freeze, scoped consistency.

Never schedule a full-workspace consistency audit solely because more than one file changed.

# Lean vs Submission

In `lean`:

- require only manifests, method card, decision ledger, probe summary, and run summaries;
- do not require per-round Markdown reports, full success logs, frozen numbers, paper artifacts, or final audits;
- persist a detailed report only at a human decision point or final round.

In `submission`:

- require final explanations, reviews, analyses, robustness, package, freeze, paper, and G6;
- run the full three-auditor layer once before final assembly.

# Compatibility

Read legacy artifacts when new ones are absent:

- `planning/progress_dashboard.md`
- `qx_method_candidates.md`
- `qx_method_iteration_log.md`
- `qx_decision_log.md`
- `decisions/*_modeler_decision.md`
- Markdown code reviews

Also accept manifests without `source_registry`, `feature_spec`, `feature_audit`, `literature_analysis`, `robustness_summary`, or `frozen_numbers`. Add these optional keys only at the next material state update; do not bump the schema solely for this integration.

Mark them `legacy_source` in the manifest and recommend migration at the next material edit. Do not regenerate legacy files for new work.

# Output

Return a compact state report:

- profile;
- per-question current gate and blocker;
- artifacts changed or missing;
- change-impact class;
- one next action;
- optional runners-up only when they can proceed independently.

Do not paste a full dashboard or large JSON structure unless the user asks.

# Verification

- State is derived from current canonical artifacts.
- Lean requirements are not confused with submission requirements.
- Human decisions were not inferred from AI suggestions.
- Code generation, freeze, paper writing, and final assembly flags match the gates.
- Audit scope matches semantic impact.
- Manifest and reported next action agree.
