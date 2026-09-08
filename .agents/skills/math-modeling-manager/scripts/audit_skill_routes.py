#!/usr/bin/env python3
"""Audit the project-scoped mathematical-modeling skill registry and routes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


MANAGER_REQUIRED = (
    "SKILL.md",
    "references/workflow.md",
    "references/routing-matrix.md",
    "references/method-scenarios.md",
    "references/evidence-policy.md",
    "references/failure-playbook.md",
    "references/skill-registry.json",
    "assets/session_config.template.json",
    "scripts/audit_skill_routes.py",
    "evals/routing_cases.json",
)

ORCHESTRATOR_REQUIRED = (
    "SKILL.md",
    "references/state-machine.md",
    "references/step-contract.md",
    "references/checkpoint-policy.md",
    "references/workflow-schema.json",
    "assets/cumcm-submission.template.json",
    "assets/lean.template.json",
    "scripts/workflow.py",
    "scripts/checks/environment_check.py",
    "scripts/checks/artifact_check.py",
    "scripts/checks/data_ingest_check.py",
    "scripts/checks/leakage_check.py",
    "scripts/checks/method_reference_check.py",
    "scripts/checks/modeling_coverage_check.py",
    "scripts/checks/claim_code_check.py",
    "scripts/checks/frozen_number_check.py",
    "scripts/checks/reference_check.py",
    "scripts/checks/delivery_check.py",
    "scripts/checks/docx_delivery_check.py",
    "scripts/contracts.py",
    "scripts/smoke_case.py",
    "references/runtime-contract.md",
)

LATEX_ZH_REQUIRED = (
    "SKILL.md",
    "scripts/compile_latex.py",
    "scripts/check_latex_delivery.py",
    "scripts/export_docx.py",
    "scripts/check_docx_delivery.py",
    "evals/test_latex_tools.py",
)

BUILTIN_CHECKS = {"human_decision_check", "git_context_check", "evidence_check", "scientific_check", "audit_check"}

FORBIDDEN_SKILL_REFS = (
    "choosing-a-forecaster",
    "autocorrelation-and-lag-selection",
    "baseline-forecasting",
    "hyperparameter-optimization",
    "prediction-intervals",
    "troubleshooting-common-errors",
    "problem-parser",
    "problem-classifier",
    "decision-prompt-builder",
    "modeler-decision-logger",
    "result-report-generator",
    "completeness-auditor",
    "consistency-auditor",
    "forecasting-single-series",
    "code-reviewer",
    "baseline_check",
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

    orchestrator_dir = skill_root / "workflow-orchestrator"
    for rel in ORCHESTRATOR_REQUIRED:
        if not (orchestrator_dir / rel).exists():
            errors.append(f"missing orchestrator file: {rel}")
    artifact_contracts = {}
    contract_path = orchestrator_dir / "assets" / "artifact-contracts.json"
    if not contract_path.exists():
        errors.append("missing canonical artifact contract")
    else:
        artifact_contracts = load_json(contract_path).get("contracts", {})

    latex_zh_dir = skill_root / "latex-paper-zh"
    for rel in LATEX_ZH_REQUIRED:
        if not (latex_zh_dir / rel).exists():
            errors.append(f"missing Chinese LaTeX delivery file: {rel}")

    session_template = load_json(manager_dir / "assets" / "session_config.template.json")
    if session_template.get("delivery_mode") != "latex_primary_docx_mirror":
        errors.append("submission session default must use the canonical-LaTeX DOCX mirror mode")

    registry = load_json(registry_path)
    entries = registry.get("skills", [])
    registry_names = [entry.get("name") for entry in entries]
    registry_set = set(registry_names)
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

    template_summaries = []
    for template_name in ("cumcm-submission.template.json", "lean.template.json"):
        path = orchestrator_dir / "assets" / template_name
        if not path.exists():
            continue
        template = load_json(path)
        defaults = template.get("defaults", {})
        if defaults.get("delivery_mode") not in {"single", "latex_primary_docx_mirror"}:
            errors.append(f"template {template_name} has invalid default delivery_mode")
        steps = template.get("steps", [])
        step_ids = [step.get("id") for step in steps]
        gate_order = {name: index for index, name in enumerate(("G0", "G1", "G2", "G2.5", "G3", "G4", "G5", "G6"))}
        previous_gate = -1
        checkpoint_count = 0
        if len(step_ids) != len(set(step_ids)):
            errors.append(f"duplicate step ids in {template_name}")
        for step in steps:
            skill = step.get("skill")
            if skill not in registry_set:
                errors.append(f"template {template_name} has missing skill: {skill}")
            for variants_name in ("language_variants", "paper_format_variants"):
                variants = step.get(variants_name, {})
                if not isinstance(variants, dict):
                    errors.append(f"template {template_name} step {step.get('id')} has invalid {variants_name}")
                    continue
                for variant_name, variant in variants.items():
                    variant_skill = variant.get("skill") if isinstance(variant, dict) else None
                    if variant_skill and variant_skill not in registry_set:
                        errors.append(
                            f"template {template_name} step {step.get('id')} variant {variant_name} "
                            f"has missing skill: {variant_skill}"
                        )
            delivery_modes = step.get("delivery_modes", [])
            if not isinstance(delivery_modes, list) or any(
                mode not in {"single", "latex_primary_docx_mirror"} for mode in delivery_modes
            ):
                errors.append(f"template {template_name} step {step.get('id')} has invalid delivery_modes")
            for field in ("id", "outputs", "checks", "gate_after"):
                if field not in step:
                    errors.append(f"template {template_name} step {step.get('id')} missing {field}")
            for check in step.get("checks", []):
                if check in BUILTIN_CHECKS:
                    continue
                if not (orchestrator_dir / "scripts" / "checks" / f"{check}.py").exists():
                    errors.append(f"template {template_name} has missing check: {check}")
            if step.get("id") in artifact_contracts:
                for contract in artifact_contracts[step["id"]]:
                    if contract.get("output_index", 0) >= len(step.get("outputs", [])):
                        errors.append(f"template {template_name} step {step.get('id')} has no output for artifact contract")
            current_gate = gate_order.get(step.get("gate_after"), -1)
            if current_gate < previous_gate:
                errors.append(f"template {template_name} gates are not monotonic at {step.get('id')}")
            previous_gate = max(previous_gate, current_gate)
            checkpoint = step.get("checkpoint")
            if checkpoint:
                checkpoint_count += 1
                if checkpoint.get("reason") not in ALLOWED_PAUSES:
                    errors.append(f"template {template_name} has invalid checkpoint reason: {checkpoint.get('reason')}")
                if checkpoint.get("policy") != "never_auto_approve":
                    errors.append(f"template {template_name} checkpoint can auto-approve: {step.get('id')}")
                if not checkpoint.get("decision_type"):
                    errors.append(f"template {template_name} checkpoint lacks decision_type: {step.get('id')}")
        declared = template.get("human_checkpoints", [])
        declared_reasons = {item.get("reason") for item in declared}
        if declared_reasons != ALLOWED_PAUSES:
            errors.append(f"template {template_name} must declare exactly four pause types")
        if any(item.get("policy") != "never_auto_approve" for item in declared):
            errors.append(f"template {template_name} contains an auto-approving checkpoint")
        if checkpoint_count != 4:
            errors.append(f"template {template_name} must expose exactly four checkpoint definitions, found {checkpoint_count}")
        template_summaries.append({"template": template_name, "steps": len(steps)})

    submission = load_json(orchestrator_dir / "assets" / "cumcm-submission.template.json")
    submission_steps = {step.get("id"): step for step in submission.get("steps", [])}
    docx_step = submission_steps.get("docx-export")
    if not docx_step or docx_step.get("delivery_modes") != ["latex_primary_docx_mirror"]:
        errors.append("submission template lacks the canonical-LaTeX DOCX mirror route")

    cases = load_json(cases_path).get("cases", [])
    if len(cases) < 30:
        errors.append(f"at least 30 routing cases required, found {len(cases)}")
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
        "templates": template_summaries,
    }
    return errors, summary


def run_smoke() -> dict:
    workflow_path = Path(__file__).resolve().parents[2] / "workflow-orchestrator" / "scripts" / "workflow.py"
    spec = importlib.util.spec_from_file_location("math_modeling_workflow_runtime", workflow_path)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load workflow runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.smoke_test()


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
