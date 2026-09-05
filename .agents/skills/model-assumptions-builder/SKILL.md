---
name: model-assumptions-builder
description: 从题意、方法契约和数据中整理模型假设、符号、准备工作及推导，主动评价假设的必要性与影响，供建模、结果展示和论文使用。
---

# Inputs

- problem parse;
- active method cards;
- data profile and risk-probe summaries;
- question dependency map;
- existing assumptions and human decisions.

Read legacy candidate pools only during migration.

# Workflow

1. Extract explicit problem assumptions and method-induced assumptions.
2. Remove filler statements that do not affect model validity or interpretation.
3. For each assumption record:
   - scope and source;
   - modeling need;
   - applicable method/Qx;
   - validation evidence;
   - mitigation or fallback link.
4. Identify conflicts across Qx.
5. Analyze necessity, impact and conflicts proactively. Ask only when a conflict changes framing, final method or claim scope; use the existing judgment point.
6. Keep AI analysis distinct from actual user decisions; do not invent the user's rationale.
7. Save per-question `methods/Qx/qx_foundations.json` with assumptions, symbols, preparation and derivations. Include concrete statements, units, sources, validation and scope. Global assumption/symbol summaries may be derived from these records.

# Assumption Fields

- ID;
- statement;
- scope;
- source and modeling need;
- human-confirmed type: necessary or simplifying;
- validation method/evidence;
- impact if violated;
- mitigation/fallback;
- decision ID.

# Rules

- Do not invent generic assumptions such as “data are accurate” unless they affect a real dependency.
- Derive necessary/simplifying labels and impacts as evidence-backed analysis; user approval of model/claims governs final adoption.
- Revisit an assumption only when its method, evidence, or downstream use materially changes.

# Verification

- Every assumption has a modeling need and source.
- Human-owned labels trace to decisions.
- Probe/robustness evidence addresses load-bearing assumptions.
- Cross-Qx conflicts are resolved or explicit.
