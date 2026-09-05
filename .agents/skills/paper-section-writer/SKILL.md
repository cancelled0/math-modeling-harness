---
name: paper-section-writer
description: Draft submission-ready mathematical-modeling paper sections from the approved solution package, frozen numbers, human decision ledger, and verified figures without searching scattered exploratory outputs or inventing interpretation.
---

# Preconditions

- `rigor_profile` is `submission`.
- Final method explanation exists.
- Final result analysis exists.
- Solution package and current frozen numbers exist.
- Required human claim-scope and physical/domain-meaning decisions are recorded.

If any prerequisite is missing, return to its producer rather than drafting around the gap.

# Primary Sources

Use, in order:

1. `qx_solution_package_for_writer.md`
2. `frozen_numbers.json`
3. `qx_decisions.jsonl`
4. verified paper figures/tables
5. final method explanation and robustness report for clarification

Do not hunt through raw experiment folders to invent a narrative.

# Workflow

1. Resolve the requested section and contest format.
2. Build a claim map:
   - claim ID;
   - frozen value/source;
   - robustness support;
   - human decision ID;
   - figure/table reference;
   - limitation.
3. Draft the method description to match the final explanation and code.
4. Draft results with:
   - value and comparison;
   - human-confirmed physical/domain meaning;
   - uncertainty or robustness;
   - limitation and applicable scope.
5. Mention the baseline and eliminated alternatives only when they explain a real decision.
6. Use only Type 2–4 figures as appropriate; never place Type 1 diagnostics in the paper.
7. Save `paper/drafts/qx.tex` or the requested Markdown draft. The polisher writes the verified `paper/sections/qx.tex` (or `.md`) so downstream editing does not mutate the upstream draft.
8. For Chinese LaTeX delivery, hand off frozen, verified sections to `latex-paper-zh`; for explicit English LaTeX, use `latex-paper-en`. In `latex_primary_docx_mirror` mode, do not author a second Word manuscript: compile and verify LaTeX first, then let `latex-paper-zh` derive the DOCX from the same canonical source. Only when session configuration explicitly selects Word/Markdown as the primary format should the available document and PDF-render capabilities assemble `paper/main.docx` or `paper/main.md` independently.

# Human-Owned Content

The AI may derive method rationale, physical interpretations, limitations and contribution framing from evidence. Distinguish established findings, AI analysis and interpretations awaiting confirmation. The user approves the final method, result acceptance and claim scope through the existing four judgment types; do not ask them to author every explanation. Record actual user adoption faithfully, never invent human-authored reasons. Reuse the accepted modeling-results-presenter report as a readable source alongside frozen numbers.

# Rules

- Every numerical claim must match `frozen_numbers.json`.
- Do not overclaim against untested methods or populations.
- Do not fabricate citations or causal meaning.
- Avoid procedural diary prose and ceremonial detail.
- Keep formulas, symbols, units, captions, and filenames consistent.
- Do not create a new decision artifact.

# Verification

- Three writer prerequisites pass.
- Claim map resolves all numbers and judgments.
- Method, results, and figures match canonical artifacts.
- Physical meaning and contribution are evidence-backed and remain within the approved claim scope.
- Limitations and uncertainty are visible.
- No Type 1 figure appears.
- The selected delivery Skill matches the configured language and format.
