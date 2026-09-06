---
name: modeler-decision-logger
description: Faithfully append a human modeler's choice and rationale to one canonical per-subquestion JSONL decision ledger. Use after a choice card is answered or when migrating legacy decision artifacts; never originate or improve the decision.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Purpose

Make human judgment traceable without multiplying decision files.

# Canonical Output

`methods/Qx/qx_decisions.jsonl`

One JSON object per line. Records are append-only.

Use `planning/framing_decisions.jsonl` for global/pre-Qx framing decisions.

# Required Fields

```json
{
  "schema_version": 1,
  "decision_id": "q1_method_choice",
  "decision_type": "method_choice",
  "status": "DECIDED",
  "decided_by": "human",
  "captured_in_mode": "learning",
  "choice": "M2",
  "user_message": "用户明确选择的原话",
  "rationale": null,
  "experiment_id": "当前实验编号；全局判断为 null",
  "selected_method": "仅方法选择填写用户选定的方法 ID",
  "evidence_hashes": {"实际证据相对路径": "由 decision-context 计算的 SHA256"},
  "evidence_refs": ["methods/Q1/probes/risk_probe_summary.json"],
  "decided_at": "ISO-8601",
  "supersedes": null
}
```

Optional structured fields may include confidence, rejected alternatives, round action, claim scope, assumption labels, or fallback activation.

# Workflow

1. Receive the human's answer, the choice-card ID, and evidence paths. Prefer `workflow.py record-decision --question Qx --step <checkpoint> --choice <choice> --user-message <actual answer>`; for method choice supply `--selected-method`. It captures current hashes and experiment ID automatically. Use structured subprocess arguments for user text, never interpolate it as shell code.
2. Preserve the user's meaning and wording. Normalize only structure, identifiers, and whitespace.
3. Verify:
   - the choice is one of the presented options or explicitly records a user-supplied alternative;
   - evidence paths exist;
   - rationale preserves an explicitly supplied reason, or is null when the user simply agrees; do not ask for a reason solely to fill this field;
   - the record does not falsely label AI-authored prose as human-authored.
4. Append one JSON line.
5. If revising a decision, append a new record with `supersedes`; never overwrite history.
6. Update the compact history in `qx_method_card.md` only when the decision changes method state.
7. Return to the orchestrator's start/finish validation; do not directly edit manifest gate/status fields.

# Decision Types

Typical values:

- `framing`
- `method_choice`
- `fallback_activation`
- `result_verdict`
- `stability_verdict`
- `assumption_necessity`
- `claim_scope`
- `package_signoff`
- `submission_authorization`

# Staleness

Mark a decision stale only when its cited evidence materially changed:

- append a `decision_stale` record naming the old decision and changed evidence;
- ask the human to reconfirm through one choice card;
- do not mark decisions stale because unrelated files or formatting changed.

# Legacy Migration

Read legacy:

- `methods/Qx/qx_decision_log.md`
- `methods/Qx/decisions/*_modeler_decision.md`

Migrate only completed human decisions. Preserve original timestamps and source paths when available. Do not convert PENDING placeholders into decisions.

# Rules

- Never choose, rationalize, strengthen, or complete the user's decision.
- Never create a separate pending decision artifact.
- Never copy `ai_suggestion` into the human rationale.
- One evidence-linked sentence is enough; do not impose arbitrary prose length.
- Preserve an honest AI-use provenance distinction.

# Verification

- JSONL is valid one-object-per-line.
- Record is append-only and uniquely identified.
- Human ownership and evidence are accurate.
- Supersession and staleness preserve history.
