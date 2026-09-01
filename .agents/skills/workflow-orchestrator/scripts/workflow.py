#!/usr/bin/env python3
"""File-backed runtime for the project mathematical-modeling workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSET_DIR = SKILL_DIR / "assets"
CHECK_DIR = SCRIPT_DIR / "checks"
GATE_ORDER = {"G0": 0, "G1": 1, "G2": 2, "G2.5": 3, "G3": 4, "G4": 5, "G5": 6, "G6": 7}
BUILTIN_CHECKS = {"human_decision_check", "git_context_check"}


class WorkflowError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def template_path(profile: str) -> Path:
    name = "cumcm-submission.template.json" if profile == "submission" else "lean.template.json"
    return ASSET_DIR / name


def load_template(profile: str) -> dict[str, Any]:
    template = read_json(template_path(profile))
    if template.get("profile") != profile:
        raise WorkflowError(f"template profile mismatch: {template_path(profile)}")
    return template


def runtime_paths(workspace: Path) -> dict[str, Path]:
    planning = workspace / "planning"
    return {
        "run": planning / "workflow_run.json",
        "session": planning / "session_config.json",
        "artifacts": planning / "artifacts.json",
        "events": planning / "events.jsonl",
        "experiments": planning / "experiment_registry.jsonl",
        "manifests": planning / "manifests",
    }


def manifest_path(workspace: Path, question: str) -> Path:
    return runtime_paths(workspace)["manifests"] / f"{question}.json"


def normalize_question(raw: str) -> str:
    value = raw.strip().upper()
    if not re.fullmatch(r"Q[1-9][0-9]*", value):
        raise WorkflowError(f"invalid question id: {raw}")
    return value


def render(value: str, question: str) -> str:
    return value.format(question=question, question_lower=question.lower())


def applicable_steps(template: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    paper_format = config.get("paper_format", template.get("defaults", {}).get("paper_format"))
    language = config.get("implementation_language", "auto")
    if language == "auto":
        language = "python"
    result = []
    for raw_step in template.get("steps", []):
        step = dict(raw_step)
        variant = raw_step.get("language_variants", {}).get(language)
        if variant:
            step.update(variant)
        paper_variant = raw_step.get("paper_format_variants", {}).get(paper_format)
        if paper_variant:
            step.update(paper_variant)
        formats = step.get("paper_formats")
        if formats and paper_format not in formats:
            continue
        result.append(step)
    return result


def outputs_for(step: dict[str, Any], question: str) -> list[str]:
    return [render(item, question) for item in step.get("outputs", [])]


def git_context(workspace: Path) -> dict[str, Any]:
    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=workspace,
        text=True, encoding="utf-8", errors="replace", capture_output=True,
    )
    if probe.returncode or probe.stdout.strip() != "true":
        return {"available": False, "branch": None, "commit": None, "dirty": None}
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=workspace,
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=True,
    ).stdout.strip()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace,
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=True,
    ).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=workspace,
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=True,
    ).stdout.strip())
    return {"available": True, "branch": branch, "commit": commit, "dirty": dirty}


def latest_decision(path: Path, decision_type: str, after: str | None = None) -> dict[str, Any] | None:
    if not path.exists():
        return None
    after_time = parse_time(after)
    candidate = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            item.get("decision_type") == decision_type
            and item.get("status") == "DECIDED"
            and item.get("decided_by") == "human"
        ):
            decided_at = parse_time(item.get("decided_at"))
            if after_time and (not decided_at or decided_at <= after_time):
                continue
            candidate = item
    return candidate


def output_valid(path: Path, after: str | None = None) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    after_time = parse_time(after)
    if after_time:
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified <= after_time:
            return False
    if path.suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
    return True


def step_record(manifest: dict[str, Any], step_id: str) -> dict[str, Any]:
    return manifest.setdefault("steps", {}).setdefault(step_id, {"status": "pending"})


def step_complete(workspace: Path, manifest: dict[str, Any], step: dict[str, Any]) -> bool:
    record = step_record(manifest, step["id"])
    if record.get("status") in {"running", "failed", "stale"}:
        return False
    stale_since = record.get("stale_since")
    checkpoint = step.get("checkpoint")
    if checkpoint:
        decision_relative = checkpoint.get("decision_file") or outputs_for(step, manifest["question_id"])[0]
        decision_file = workspace / render(decision_relative, manifest["question_id"])
        if not latest_decision(decision_file, checkpoint["decision_type"], stale_since):
            return False
    for relative in outputs_for(step, manifest["question_id"]):
        if not output_valid(workspace / relative, stale_since):
            return False
    return True


def derive_question(
    workspace: Path,
    run: dict[str, Any],
    template: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    steps = applicable_steps(template, run["config"])
    current_gate = "G0"
    next_step = None
    for step in steps:
        record = step_record(manifest, step["id"])
        if step_complete(workspace, manifest, step):
            if record.get("status") != "stale":
                record["status"] = "completed"
            gate = step.get("gate_after", current_gate)
            if GATE_ORDER.get(gate, -1) > GATE_ORDER.get(current_gate, -1):
                current_gate = gate
            continue
        next_step = step
        if step.get("checkpoint"):
            record["status"] = "waiting_human"
        elif record.get("status") not in {"running", "failed", "stale"}:
            record["status"] = "ready"
        break

    method_chosen = any(
        step["id"] == "method-choice" and step_complete(workspace, manifest, step) for step in steps
    )
    frozen = any(step["id"] == "freeze" and step_complete(workspace, manifest, step) for step in steps)
    paper_ready = any(
        step["id"] in {"latex-build", "word-build", "markdown-build"}
        and step_complete(workspace, manifest, step)
        for step in steps
    )
    complete = next_step is None
    manifest["current_gate"] = "G6" if complete and run["profile"] == "submission" else current_gate
    manifest["status"] = "completed" if complete else step_record(manifest, next_step["id"])["status"]
    manifest["allowed"] = {
        "code_generation": method_chosen,
        "freeze": current_gate in {"G3", "G4", "G5", "G6"},
        "paper_writing": frozen,
        "final_assembly": complete or paper_ready,
    }
    manifest["blockers"] = []
    if next_step and next_step.get("checkpoint"):
        manifest["blockers"].append(next_step["checkpoint"]["reason"])
    manifest["next_action"] = None if complete else {
        "owner": "human" if next_step.get("checkpoint") else "agent",
        "step": next_step["id"],
        "skill": next_step["skill"],
        "outputs": outputs_for(next_step, manifest["question_id"]),
        "checks": next_step.get("checks", []),
        "checkpoint": next_step.get("checkpoint"),
    }
    manifest["updated_at"] = now()
    return manifest


def load_runtime(workspace: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = runtime_paths(workspace)
    if not paths["run"].exists():
        raise WorkflowError("workflow is not initialized")
    run = read_json(paths["run"])
    return run, load_template(run["profile"])


def load_manifest(workspace: Path, question: str) -> dict[str, Any]:
    path = manifest_path(workspace, question)
    if not path.exists():
        raise WorkflowError(f"manifest does not exist: {question}")
    return read_json(path)


def save_manifest(workspace: Path, manifest: dict[str, Any]) -> None:
    write_json(manifest_path(workspace, manifest["question_id"]), manifest)


def record_event(workspace: Path, event: str, **fields: Any) -> None:
    append_jsonl(runtime_paths(workspace)["events"], {
        "schema_version": 1, "event": event, "recorded_at": now(), **fields,
    })


def initial_manifest(question: str, profile: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "question_id": question,
        "rigor_profile": profile,
        "current_gate": "G0",
        "status": "ready",
        "artifacts": {},
        "steps": {},
        "allowed": {
            "code_generation": False,
            "freeze": False,
            "paper_writing": False,
            "final_assembly": False,
        },
        "blockers": [],
        "next_action": {"owner": "agent", "step": "problem-parse", "skill": "problem-parser"},
        "updated_at": now(),
    }


def cmd_init(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    paths = runtime_paths(workspace)
    if paths["run"].exists():
        raise WorkflowError("workflow_run.json already exists; refusing to overwrite")
    template = load_template(args.profile)
    questions = [normalize_question(item) for item in args.questions.split(",") if item.strip()]
    if not questions or len(questions) != len(set(questions)):
        raise WorkflowError("questions must be a non-empty unique comma-separated list")
    git = git_context(workspace)
    if not git["available"] and not args.allow_no_git:
        raise WorkflowError("formal harness requires a Git repository; pass --allow-no-git only for isolated diagnostics")
    defaults = dict(template.get("defaults", {}))
    defaults.update({
        "contest_profile": args.contest,
        "paper_format": args.paper_format or defaults.get("paper_format"),
        "implementation_language": args.language,
        "random_seed": args.seed,
    })
    run = {
        "schema_version": 1,
        "workflow_id": args.workflow_id,
        "profile": args.profile,
        "template": template_path(args.profile).name,
        "status": "running",
        "questions": questions,
        "config": defaults,
        "git_at_init": git,
        "created_at": now(),
        "updated_at": now(),
    }
    write_json(paths["run"], run)
    if not paths["session"].exists():
        write_json(paths["session"], {
            "schema_version": 1,
            "contest_profile": args.contest,
            "rigor_profile": args.profile,
            "interaction_mode": "speed",
            "implementation_language": args.language,
            "paper_language": defaults.get("paper_language", "zh-CN"),
            "paper_format": defaults.get("paper_format", "latex"),
            "random_seed": args.seed,
            "active_questions": questions,
            "version_control": {"enabled": git["available"], "stable_branch": git.get("branch") or "main"},
        })
    write_json(paths["artifacts"], {"schema_version": 1, "items": []})
    paths["events"].parent.mkdir(parents=True, exist_ok=True)
    paths["events"].touch(exist_ok=True)
    paths["experiments"].touch(exist_ok=True)
    for question in questions:
        manifest = derive_question(workspace, run, template, initial_manifest(question, args.profile))
        save_manifest(workspace, manifest)
    record_event(workspace, "workflow_initialized", workflow_id=args.workflow_id, questions=questions, profile=args.profile)
    return {"status": "INITIALIZED", "workflow": run, "next": cmd_next(workspace, argparse.Namespace(question=None))}


def cmd_status(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    run, template = load_runtime(workspace)
    questions = [normalize_question(args.question)] if getattr(args, "question", None) else run["questions"]
    states = []
    for question in questions:
        manifest = derive_question(workspace, run, template, load_manifest(workspace, question))
        states.append({
            "question_id": question,
            "gate": manifest["current_gate"],
            "status": manifest["status"],
            "blockers": manifest["blockers"],
            "next_action": manifest["next_action"],
        })
    return {"workflow_id": run["workflow_id"], "profile": run["profile"], "status": run["status"], "git": git_context(workspace), "questions": states}


def cmd_next(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    run, template = load_runtime(workspace)
    if run["status"] == "paused":
        return {"status": "PAUSED", "reason": run.get("pause_reason")}
    questions = [normalize_question(args.question)] if getattr(args, "question", None) else run["questions"]
    for question in questions:
        manifest = derive_question(workspace, run, template, load_manifest(workspace, question))
        if manifest["next_action"]:
            return {"status": "READY", "question_id": question, **manifest["next_action"]}
    return {"status": "COMPLETE", "question_ids": questions}


def resolve_step(
    workspace: Path, run: dict[str, Any], template: dict[str, Any], question: str, requested: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = derive_question(workspace, run, template, load_manifest(workspace, question))
    action = manifest.get("next_action")
    if not action:
        raise WorkflowError(f"{question} is complete")
    step_id = requested or action["step"]
    if step_id != action["step"]:
        raise WorkflowError(f"expected next step {action['step']}, got {step_id}")
    step = next((item for item in applicable_steps(template, run["config"]) if item["id"] == step_id), None)
    if not step:
        raise WorkflowError(f"step not found in active template: {step_id}")
    return manifest, step


def cmd_start(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    run, template = load_runtime(workspace)
    if run["status"] == "paused":
        raise WorkflowError("workflow is paused")
    question = normalize_question(args.question)
    manifest, step = resolve_step(workspace, run, template, question, args.step)
    record = step_record(manifest, step["id"])
    record.update({"status": "running", "started_at": now(), "git": git_context(workspace), "error": None})
    save_manifest(workspace, manifest)
    record_event(workspace, "step_started", question_id=question, step=step["id"], skill=step["skill"])
    return {"status": "RUNNING", "question_id": question, "step": step["id"], "skill": step["skill"]}


def validate_step(workspace: Path, manifest: dict[str, Any], step: dict[str, Any]) -> list[str]:
    errors = []
    record = step_record(manifest, step["id"])
    stale_since = record.get("stale_since")
    for relative in outputs_for(step, manifest["question_id"]):
        if not output_valid(workspace / relative, stale_since):
            errors.append(f"missing, invalid, or stale output: {relative}")
    checkpoint = step.get("checkpoint")
    if checkpoint:
        decision_relative = checkpoint.get("decision_file") or outputs_for(step, manifest["question_id"])[0]
        decision_path = workspace / render(decision_relative, manifest["question_id"])
        if not latest_decision(decision_path, checkpoint["decision_type"], stale_since):
            errors.append(f"missing fresh human DECIDED record: {checkpoint['decision_type']}")
    return errors


def update_artifact_index(workspace: Path, question: str, step: dict[str, Any], outputs: list[str]) -> None:
    path = runtime_paths(workspace)["artifacts"]
    index = read_json(path)
    items = [item for item in index.get("items", []) if not (item.get("question_id") == question and item.get("step") == step["id"])]
    for relative in outputs:
        item_path = workspace / relative
        items.append({
            "question_id": question,
            "step": step["id"],
            "artifact_key": step.get("artifact_key"),
            "path": relative,
            "size": item_path.stat().st_size,
            "updated_at": now(),
            "git": git_context(workspace),
        })
    index["items"] = items
    write_json(path, index)


def cmd_finish(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    run, template = load_runtime(workspace)
    question = normalize_question(args.question)
    manifest, step = resolve_step(workspace, run, template, question, args.step)
    errors = validate_step(workspace, manifest, step)
    record = step_record(manifest, step["id"])
    if errors:
        record.update({"status": "failed", "error": errors, "completed_at": now()})
        save_manifest(workspace, manifest)
        record_event(workspace, "step_failed", question_id=question, step=step["id"], errors=errors)
        raise WorkflowError("; ".join(errors))
    outputs = outputs_for(step, question)
    record.update({
        "status": "completed", "completed_at": now(), "outputs": outputs,
        "git": git_context(workspace), "error": None,
    })
    record.pop("stale_since", None)
    if step.get("artifact_key") and outputs:
        manifest.setdefault("artifacts", {})[step["artifact_key"]] = outputs[0]
    update_artifact_index(workspace, question, step, outputs)
    manifest = derive_question(workspace, run, template, manifest)
    save_manifest(workspace, manifest)
    record_event(workspace, "step_completed", question_id=question, step=step["id"], outputs=outputs)
    return {"status": "COMPLETED", "question_id": question, "step": step["id"], "next": manifest["next_action"]}


def cmd_pause(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    run, _ = load_runtime(workspace)
    run.update({"status": "paused", "pause_reason": args.reason, "updated_at": now()})
    write_json(runtime_paths(workspace)["run"], run)
    record_event(workspace, "workflow_paused", reason=args.reason)
    return {"status": "PAUSED", "reason": args.reason}


def cmd_resume(workspace: Path, _: argparse.Namespace) -> dict[str, Any]:
    run, _ = load_runtime(workspace)
    run.update({"status": "running", "pause_reason": None, "updated_at": now()})
    write_json(runtime_paths(workspace)["run"], run)
    record_event(workspace, "workflow_resumed")
    return {"status": "RUNNING"}


def cmd_rerun(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    run, template = load_runtime(workspace)
    question = normalize_question(args.question)
    manifest = load_manifest(workspace, question)
    steps = applicable_steps(template, run["config"])
    ids = [step["id"] for step in steps]
    if args.from_step not in ids:
        raise WorkflowError(f"unknown active step: {args.from_step}")
    freeze_step = next((step for step in steps if step["id"] == "freeze"), None)
    freeze_was_complete = bool(freeze_step and step_complete(workspace, manifest, freeze_step))
    stamp = now()
    affected = ids[ids.index(args.from_step):]
    for step_id in affected:
        step_record(manifest, step_id).update({"status": "stale", "stale_since": stamp, "error": None})
    frozen_outputs_exist = bool(
        freeze_step
        and any((workspace / item).exists() for item in outputs_for(freeze_step, question))
    )
    if freeze_was_complete or frozen_outputs_exist:
        manifest["freeze_state"] = "thaw_required"
    manifest = derive_question(workspace, run, template, manifest)
    save_manifest(workspace, manifest)
    record_event(workspace, "steps_marked_stale", question_id=question, from_step=args.from_step, affected=affected)
    return {"status": "STALE", "question_id": question, "affected": affected, "next": manifest["next_action"]}


def cmd_check(workspace: Path, _: argparse.Namespace) -> dict[str, Any]:
    run, template = load_runtime(workspace)
    errors = []
    step_ids = [step["id"] for step in applicable_steps(template, run["config"])]
    if len(step_ids) != len(set(step_ids)):
        errors.append("duplicate active step ids")
    for step in applicable_steps(template, run["config"]):
        for check in step.get("checks", []):
            if check in BUILTIN_CHECKS:
                continue
            if not (CHECK_DIR / f"{check}.py").exists():
                errors.append(f"missing check implementation: {check}")
    questions = []
    for question in run["questions"]:
        manifest = derive_question(workspace, run, template, load_manifest(workspace, question))
        questions.append({"question_id": question, "gate": manifest["current_gate"], "next": manifest["next_action"]})
    return {"status": "PASSED" if not errors else "FAILED", "errors": errors, "questions": questions}


def cmd_compare(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    script = SKILL_DIR.parent / "git-experiment-manager" / "scripts" / "compare_experiments.py"
    command = [sys.executable, str(script), str((workspace / args.left).resolve()), str((workspace / args.right).resolve())]
    if args.output:
        command.extend(["--output", str((workspace / args.output).resolve())])
    process = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if process.returncode not in {0, 2}:
        raise WorkflowError(process.stdout or process.stderr)
    result = json.loads(process.stdout)
    result["exit_code"] = process.returncode
    return result


def cmd_export(workspace: Path, args: argparse.Namespace) -> dict[str, Any]:
    destination = args.destination.resolve()
    if destination.exists():
        raise WorkflowError(f"destination already exists: {destination}")
    roots = ["planning", "methods", "code", "results", "robustness", "paper"]
    files = []
    for root_name in roots:
        root = workspace / root_name
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file() and "data_raw" not in path.parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(workspace).as_posix())
    return {"status": "EXPORTED", "destination": str(destination), "file_count": len(set(files))}


def create_smoke_output(workspace: Path, step: dict[str, Any], question: str) -> None:
    checkpoint = step.get("checkpoint")
    for relative in outputs_for(step, question):
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".jsonl":
            if checkpoint:
                append_jsonl(path, {
                    "schema_version": 1,
                    "decision_id": f"smoke_{checkpoint['decision_type']}",
                    "decision_type": checkpoint["decision_type"],
                    "status": "DECIDED",
                    "decided_by": "human",
                    "choice": "smoke-choice",
                    "rationale": "smoke-test human fixture",
                    "evidence_refs": [],
                    "decided_at": now(),
                })
        elif path.suffix == ".json":
            write_json(path, {"schema_version": 1, "status": "smoke"})
        elif path.suffix == ".pdf":
            path.write_bytes(b"%PDF-1.4\n% structural smoke fixture\n")
        else:
            path.write_text("smoke evidence\n", encoding="utf-8")
    if checkpoint and checkpoint.get("decision_file"):
        decision_path = workspace / render(checkpoint["decision_file"], question)
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(decision_path, {
            "schema_version": 1,
            "decision_id": f"smoke_{checkpoint['decision_type']}",
            "decision_type": checkpoint["decision_type"],
            "status": "DECIDED",
            "decided_by": "human",
            "choice": "smoke-choice",
            "rationale": "smoke-test human fixture",
            "evidence_refs": [],
            "decided_at": now(),
        })


def smoke_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="math-modeling-runtime-") as temp:
        workspace = Path(temp)
        subprocess.run(["git", "init", "-b", "main"], cwd=workspace, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Harness Smoke"], cwd=workspace, check=True)
        subprocess.run(["git", "config", "user.email", "smoke@example.invalid"], cwd=workspace, check=True)
        (workspace / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=workspace, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=workspace, capture_output=True, check=True)
        init_args = argparse.Namespace(
            profile="submission", questions="Q1", contest="CUMCM", paper_format="latex",
            language="python", seed=2026, workflow_id="smoke", allow_no_git=False,
        )
        cmd_init(workspace, init_args)
        run, template = load_runtime(workspace)
        sequence = []
        pauses = []
        while True:
            action = cmd_next(workspace, argparse.Namespace(question="Q1"))
            if action["status"] == "COMPLETE":
                break
            step = next(item for item in applicable_steps(template, run["config"]) if item["id"] == action["step"])
            if action.get("checkpoint"):
                pauses.append(action["checkpoint"]["reason"])
            cmd_start(workspace, argparse.Namespace(question="Q1", step=step["id"]))
            create_smoke_output(workspace, step, "Q1")
            cmd_finish(workspace, argparse.Namespace(question="Q1", step=step["id"]))
            sequence.append(step["id"])
        check = cmd_check(workspace, argparse.Namespace())
        rerun = cmd_rerun(workspace, argparse.Namespace(question="Q1", from_step="model-run"))
        if rerun["next"]["step"] != "model-run":
            raise AssertionError("rerun did not return to model-run")
        configured_pauses = [item["reason"] for item in template["human_checkpoints"]]
        if any(item["policy"] != "never_auto_approve" for item in template["human_checkpoints"]):
            raise AssertionError("a checkpoint can auto-approve")
        return {
            "status": "PASSED",
            "steps": sequence,
            "observed_path_pauses": pauses,
            "configured_human_pauses": configured_pauses,
            "rerun_next": rerun["next"]["step"],
            "runtime_check": check["status"],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--profile", choices=("lean", "submission"), default="submission")
    init.add_argument("--questions", default="Q1")
    init.add_argument("--contest", default="CUMCM")
    init.add_argument("--paper-format", choices=("latex", "word", "markdown", "none"))
    init.add_argument("--language", choices=("auto", "python", "matlab"), default="auto")
    init.add_argument("--seed", type=int, default=2026)
    init.add_argument("--workflow-id", default="math-modeling-session")
    init.add_argument("--allow-no-git", action="store_true")

    for name in ("status", "next"):
        action = sub.add_parser(name)
        action.add_argument("--question")
    for name in ("start", "finish"):
        action = sub.add_parser(name)
        action.add_argument("--question", required=True)
        action.add_argument("--step")
    pause = sub.add_parser("pause")
    pause.add_argument("--reason", required=True)
    sub.add_parser("resume")
    rerun = sub.add_parser("rerun")
    rerun.add_argument("--question", required=True)
    rerun.add_argument("--from-step", required=True)
    sub.add_parser("check")
    compare = sub.add_parser("compare")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.add_argument("--output")
    export = sub.add_parser("export")
    export.add_argument("--destination", type=Path, required=True)
    sub.add_parser("smoke")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = args.workspace.resolve()
    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "next": cmd_next,
        "start": cmd_start,
        "finish": cmd_finish,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "rerun": cmd_rerun,
        "check": cmd_check,
        "compare": cmd_compare,
        "export": cmd_export,
        "smoke": lambda _workspace, _args: smoke_test(),
    }
    try:
        result = handlers[args.command](workspace, args)
    except (WorkflowError, OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        print(json.dumps({"status": "FAILED", "error": detail}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAILED" else 1


if __name__ == "__main__":
    sys.exit(main())
