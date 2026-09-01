#!/usr/bin/env python3
"""Audit the project-scoped mathematical-modeling skill registry and routes."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path


MANAGER_REQUIRED = (
    "SKILL.md",
    "references/workflow.md",
    "references/routing-matrix.md",
    "references/method-scenarios.md",
    "references/failure-playbook.md",
    "references/skill-registry.json",
    "assets/session_config.template.json",
    "scripts/audit_skill_routes.py",
    "evals/routing_cases.json",
)

FORBIDDEN_SKILL_REFS = (
    "choosing-a-forecaster",
    "autocorrelation-and-lag-selection",
    "baseline-forecasting",
    "hyperparameter-optimization",
    "prediction-intervals",
    "troubleshooting-common-errors",
)

ALLOWED_PAUSES = {
    "material_framing_ambiguity",
    "final_method_choice",
    "result_accept_adjust_or_fallback",
    "number_freeze_and_claim_scope",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    name = re.search(r"(?m)^name:\s*([^\s#]+)\s*$", match.group(1))
    return name.group(1).strip("'\"") if name else None


def check_markdown_links(manager_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in manager_dir.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#")):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).resolve().exists():
                errors.append(f"missing Markdown link target: {path}: {target}")
    return errors


def check_explicit_skill_refs(skill_root: Path, names: set[str]) -> list[str]:
    errors: list[str] = []
    keyword = (
        r"(?:Prerequisite|Alongside|Next|next skill is|hand off to|handoff to|"
        r"route(?:s|d)?(?: the answer)? to|invoke|调用|交给|路由至|下一技能)"
    )
    pattern = re.compile(keyword + r"[^\n`]{0,80}`([a-z0-9][a-z0-9-]{1,62})`", re.I)
    # Supporting references may have their own module routers whose names are not
    # project Skills (for example latex-paper-en's `logic` module). Cross-Skill
    # handoffs belong in entrypoints; manager references are covered separately
    # by the registry, routing-matrix coverage, and Markdown-link checks.
    for path in skill_root.rglob("SKILL.md"):
        text = path.read_text(encoding="utf-8")
        for candidate in pattern.findall(text):
            if candidate not in names:
                errors.append(f"missing explicit skill target `{candidate}` in {path}")
    return errors


def audit() -> tuple[list[str], dict]:
    script_path = Path(__file__).resolve()
    manager_dir = script_path.parents[1]
    skill_root = script_path.parents[2]
    registry_path = manager_dir / "references" / "skill-registry.json"
    cases_path = manager_dir / "evals" / "routing_cases.json"
    errors: list[str] = []

    for rel in MANAGER_REQUIRED:
        if not (manager_dir / rel).exists():
            errors.append(f"missing manager file: {rel}")

    registry = load_json(registry_path)
    entries = registry.get("skills", [])
    registry_names = [entry.get("name") for entry in entries]
    registry_set = set(registry_names)
    if len(entries) != 50:
        errors.append(f"registry must contain 50 skills, found {len(entries)}")
    if len(registry_names) != len(registry_set):
        errors.append("duplicate names in skill registry")

    skill_dirs = sorted(path for path in skill_root.iterdir() if (path / "SKILL.md").exists())
    folder_names = {path.name for path in skill_dirs}
    if folder_names != registry_set:
        errors.append(
            "registry/folder mismatch: "
            f"unregistered={sorted(folder_names - registry_set)}, "
            f"missing_folders={sorted(registry_set - folder_names)}"
        )

    frontmatter_names: list[str] = []
    for folder in skill_dirs:
        name = frontmatter_name(folder / "SKILL.md")
        if name is None:
            errors.append(f"missing/invalid frontmatter name: {folder / 'SKILL.md'}")
            continue
        frontmatter_names.append(name)
        if name != folder.name:
            errors.append(f"folder/frontmatter mismatch: {folder.name} != {name}")
    if len(frontmatter_names) != len(set(frontmatter_names)):
        errors.append("duplicate frontmatter skill names")

    categories = set(registry.get("categories", []))
    terminal = {"quality-assurance-auditor"}
    for entry in entries:
        name = entry.get("name")
        if entry.get("category") not in categories:
            errors.append(f"unclassified skill: {name}")
        for field in ("stage", "activation", "outputs", "next_skills"):
            if field not in entry:
                errors.append(f"registry entry {name} missing field: {field}")
        next_skills = entry.get("next_skills", [])
        if not next_skills and name not in terminal:
            errors.append(f"handoff dead end: {name}")
        for target in next_skills:
            if target not in registry_set:
                errors.append(f"missing registry handoff target: {name} -> {target}")

    routing_text = (manager_dir / "references" / "routing-matrix.md").read_text(encoding="utf-8")
    for name in registry_set:
        if f"`{name}`" not in routing_text:
            errors.append(f"skill absent from routing matrix: {name}")

    all_markdown = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in skill_root.rglob("*.md")
    )
    for forbidden in FORBIDDEN_SKILL_REFS:
        if f"`{forbidden}`" in all_markdown:
            errors.append(f"obsolete skill reference remains: {forbidden}")

    errors.extend(check_markdown_links(manager_dir))
    errors.extend(check_explicit_skill_refs(skill_root, registry_set))

    cases = load_json(cases_path).get("cases", [])
    if len(cases) < 20:
        errors.append(f"at least 20 routing cases required, found {len(cases)}")
    case_ids = [case.get("id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("duplicate routing case ids")
    observed_pauses: set[str] = set()
    for case in cases:
        primary = case.get("expected_primary")
        if primary not in registry_set:
            errors.append(f"routing case {case.get('id')} has missing primary: {primary}")
        for target in case.get("expected_supporting", []):
            if target not in registry_set:
                errors.append(f"routing case {case.get('id')} has missing supporting skill: {target}")
        pause = case.get("human_pause", False)
        reason = case.get("pause_reason")
        if pause:
            if reason not in ALLOWED_PAUSES:
                errors.append(f"routing case {case.get('id')} has invalid pause reason: {reason}")
            else:
                observed_pauses.add(reason)
        elif reason is not None:
            errors.append(f"routing case {case.get('id')} declares a pause reason without pausing")
    if observed_pauses != ALLOWED_PAUSES:
        errors.append(
            f"routing cases must cover exactly four human pause types; found {sorted(observed_pauses)}"
        )

    summary = {
        "skill_count": len(folder_names),
        "registry_count": len(entries),
        "routing_case_count": len(cases),
        "categories": sorted(categories),
        "human_pause_types": sorted(observed_pauses),
    }
    return errors, summary


def mock_next_action(root: Path, ambiguity: bool = False) -> tuple[str, str | None]:
    if ambiguity:
        return "decision-prompt-builder", "material_framing_ambiguity"
    checks = (
        ("planning/parse/problem_parse.json", "problem-parser", None),
        ("planning/classification/problem_classification.json", "problem-classifier", None),
        ("workspace/data/data_profile.json", "data-auditor-cleaner", None),
        ("methods/Q1/q1_method_card.md", "method-selector", None),
        ("methods/Q1/q1_decisions.jsonl", "decision-prompt-builder", "final_method_choice"),
        ("code/Q1/q1_code_plan.md", "model-code-analyzer", None),
        ("results/Q1/experiments/round1/run_summary.json", "python-model-code-generator", None),
        ("code/Q1/reviews/q1_python_review.json", "code-reviewer", None),
        ("results/Q1/reports/q1_final_result_analysis.md", "result-report-generator", "result_accept_adjust_or_fallback"),
        ("robustness/Q1/q1_robustness_summary.json", "robustness-checker", None),
        ("results/Q1/reports/frozen_numbers.json", "solution-package-builder", "number_freeze_and_claim_scope"),
        ("paper/sections/q1.md", "paper-section-writer", None),
        ("paper/audits/cross_media_consistency_audit.md", "consistency-auditor", None),
        ("paper/audits/completeness_audit.md", "completeness-auditor", None),
        ("paper/qa_report.md", "quality-assurance-auditor", None),
    )
    for relative, skill, pause_reason in checks:
        if not (root / relative).exists():
            return skill, pause_reason
    return "complete", None


def run_smoke() -> dict:
    sequence: list[str] = []
    pauses: list[str] = []
    with tempfile.TemporaryDirectory(prefix="math-modeling-skill-smoke-") as temp:
        root = Path(temp)
        ambiguous_action, ambiguous_pause = mock_next_action(root, ambiguity=True)
        if ambiguous_action != "decision-prompt-builder" or ambiguous_pause not in ALLOWED_PAUSES:
            raise AssertionError("framing ambiguity did not stop at the expected human decision")
        pauses.append(ambiguous_pause)

        artifacts = (
            ("problem-parser", "planning/parse/problem_parse.json"),
            ("problem-classifier", "planning/classification/problem_classification.json"),
            ("data-auditor-cleaner", "workspace/data/data_profile.json"),
            ("method-selector", "methods/Q1/q1_method_card.md"),
            ("decision-prompt-builder", "methods/Q1/q1_decisions.jsonl"),
            ("model-code-analyzer", "code/Q1/q1_code_plan.md"),
            ("python-model-code-generator", "results/Q1/experiments/round1/run_summary.json"),
            ("code-reviewer", "code/Q1/reviews/q1_python_review.json"),
            ("result-report-generator", "results/Q1/reports/q1_final_result_analysis.md"),
            ("robustness-checker", "robustness/Q1/q1_robustness_summary.json"),
            ("solution-package-builder", "results/Q1/reports/frozen_numbers.json"),
            ("paper-section-writer", "paper/sections/q1.md"),
            ("consistency-auditor", "paper/audits/cross_media_consistency_audit.md"),
            ("completeness-auditor", "paper/audits/completeness_audit.md"),
            ("quality-assurance-auditor", "paper/qa_report.md"),
        )
        for expected, artifact in artifacts:
            action, pause = mock_next_action(root)
            if action != expected:
                raise AssertionError(f"expected {expected}, got {action}")
            sequence.append(action)
            if pause:
                pauses.append(pause)
            path = root / artifact
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        action, pause = mock_next_action(root)
        if action != "complete" or pause is not None:
            raise AssertionError("mock workflow did not reach completion")
    if set(pauses) != ALLOWED_PAUSES or len(pauses) != 4:
        raise AssertionError(f"unexpected human pause set: {pauses}")
    return {"steps": sequence, "human_pauses": pauses, "status": "PASSED"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="run an isolated mock end-to-end gate test")
    args = parser.parse_args()
    errors, summary = audit()
    result: dict = {"status": "PASSED" if not errors else "FAILED", "summary": summary, "errors": errors}
    if args.smoke and not errors:
        result["smoke"] = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
