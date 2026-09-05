#!/usr/bin/env python3
"""Evidence-bound workflow runtime; manifest schema remains 1."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSET_DIR = SKILL_DIR / "assets"
CHECK_DIR = SCRIPT_DIR / "checks"
sys.path.insert(0, str(SCRIPT_DIR))
import contracts as c

GATE_ORDER = {"G0": 0, "G1": 1, "G2": 2, "G2.5": 3, "G3": 4, "G4": 5, "G5": 6, "G6": 7}
RUNTIME_REVISION = 2

class WorkflowError(RuntimeError):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def read_json(path):
    return c.load(path)

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)

def append_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(data, ensure_ascii=False, allow_nan=False) + "\n")

def hash_value(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def template_path(profile):
    return ASSET_DIR / ("cumcm-submission.template.json" if profile == "submission" else "lean.template.json")

def load_template(profile):
    return read_json(template_path(profile))

def runtime_paths(root):
    return {key: root / "planning" / name for key, name in {
        "run": "workflow_run.json", "session": "session_config.json", "artifacts": "artifacts.json",
        "events": "events.jsonl", "experiments": "experiment_registry.jsonl", "manifests": "manifests"}.items()}

def normalize_question(raw):
    value = raw.strip().upper()
    if not re.fullmatch(r"Q[1-9][0-9]*|GLOBAL", value):
        raise WorkflowError(f"invalid question id: {raw}")
    return value

def render(value, q):
    return value.format(question=q, question_lower=q.lower())

def outputs_for(step, q):
    return [render(p, q) for p in step.get("outputs", [])]

def manifest_path(root, q):
    return root / "planning/manifests" / f"{q}.json"

def initial_manifest(q, profile):
    return {"schema_version": 1, "question_id": q, "rigor_profile": profile, "steps": {}, "artifacts": {}}

def load_manifest(root, q):
    return read_json(manifest_path(root, q))

def save_manifest(root, manifest):
    write_json(manifest_path(root, manifest["question_id"]), manifest)

def step_record(manifest, sid):
    return manifest.setdefault("steps", {}).setdefault(sid, {"status": "pending"})

def record_event(root, event, **fields):
    append_jsonl(runtime_paths(root)["events"], {"schema_version": 1, "event": event, "recorded_at": now(), **fields})

def git_context(root):
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace", capture_output=True)
    try:
        head = git("rev-parse", "HEAD")
        if head.returncode:
            return {"available": False}
        return {"available": True, "commit": head.stdout.strip(), "branch": git("branch", "--show-current").stdout.strip(),
                "dirty": bool(git("status", "--porcelain").stdout.strip())}
    except OSError:
        return {"available": False}

def applicable_steps(template, config):
    result = []
    for raw in template["steps"]:
        step = copy.deepcopy(raw)
        step.update(raw.get("language_variants", {}).get(config.get("implementation_language", "python"), {}))
        step.update(raw.get("paper_format_variants", {}).get(config.get("paper_format"), {}))
        if step.get("paper_formats") and config.get("paper_format") not in step["paper_formats"]:
            continue
        if step.get("delivery_modes") and config.get("delivery_mode", "single") not in step["delivery_modes"]:
            continue
        if step.get("optional_config") and not config.get(step["optional_config"]):
            continue
        if step["id"] == "latex-build" and config.get("paper_language", "zh-CN").startswith("en"):
            step["skill"] = "latex-paper-en"
        result.append(step)
    return result

def load_runtime(root):
    run = read_json(runtime_paths(root)["run"])
    if run.get("runtime_revision") != RUNTIME_REVISION:
        raise WorkflowError("legacy runtime: run migrate to preserve old manifests and revalidate evidence")
    if hash_value(read_json(runtime_paths(root)["session"])) != run["session_hash"]:
        raise WorkflowError("session configuration changed: run reconfigure")
    return run, run["template_snapshot"]

def graph(root, run, template):
    nodes, last = {}, {q: None for q in run["questions"]}
    for base in applicable_steps(template, run["config"]):
        owners = ["GLOBAL"] if base.get("scope") == "global" else run["questions"]
        for q in owners:
            step = copy.deepcopy(base)
            step["question_id"] = q
            if step.get("checkpoint", {}).get("conditional_field"):
                parse = root / "planning/parse/problem_parse.json"
                field = step["checkpoint"]["conditional_field"]
                if not parse.is_file() or not read_json(parse).get(field):
                    step.pop("checkpoint")
            key = f"{q}:{step['id']}"
            deps = set(filter(None, last.values())) if q == "GLOBAL" else ({last[q]} if last[q] else set())
            deps.update(render(x, q) for x in step.get("depends_on", []))
            if step["id"] == "method-screen":
                deps.update(f"{up}:result-verdict" for up in run["config"].get("question_dependencies", {}).get(q, []))
            iteration = run.get("iterations", {}).get(q, "round1")
            for field in ("outputs", "inputs"):
                step[field] = [render(x.replace("{experiment_id}", iteration), q) for x in step.get(field, [])]
            step["run_summary"] = f"results/{q}/experiments/{iteration}/run_summary.json"
            if step["id"] == "code-plan" and run["config"].get("feature_engineering"):
                step["inputs"].extend([f"workspace/features/{q}/{q.lower()}_feature_spec.json", f"workspace/features/{q}/{q.lower()}_feature_audit.json"])
            step["dependencies"] = sorted(deps)
            nodes[key] = step
        last = {q: f"GLOBAL:{base['id']}" if owners == ["GLOBAL"] else f"{q}:{base['id']}" for q in last}
    ordered, remaining = {}, dict(nodes)
    while remaining:
        ready = [key for key, step in remaining.items() if all(dep in ordered for dep in step["dependencies"])]
        if not ready:
            raise WorkflowError("cyclic or missing step dependencies: " + ", ".join(remaining))
        for key in ready:
            ordered[key] = remaining.pop(key)
    return ordered

def latest_decision(path, decision_type, after=None):
    if not path.is_file():
        return None
    found = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("decision_type") == decision_type and item.get("status") == "DECIDED" and item.get("decided_by") == "human":
            if not after or item.get("decided_at", "") > after:
                found = item
    return found

def decision_for(root, step):
    checkpoint = step.get("checkpoint")
    if not checkpoint:
        return None
    q = step["question_id"]
    path = root / render(checkpoint.get("decision_file", f"methods/{q}/{q.lower()}_decisions.jsonl"), q)
    return latest_decision(path, checkpoint["decision_type"])

def evidence_paths(step, nodes):
    paths = list(step.get("inputs", []))
    for dep in step["dependencies"]:
        paths.extend(p for p in nodes[dep]["outputs"] if not p.endswith(".jsonl"))
    if step.get("checkpoint"):
        paths.extend(p for p in step["outputs"] if not p.endswith(".jsonl"))
    return paths

def binding(root, step, nodes):
    return c.fingerprints(root, evidence_paths(step, nodes))

def snapshot(root, step, nodes):
    data = c.fingerprints(root, [p for p in step["outputs"] if not p.endswith(".jsonl")] + evidence_paths(step, nodes))
    if step.get("checkpoint"):
        data["@decision"] = hash_value(decision_for(root, step))
    if step.get("delivery_artifact") or step["id"] == "visual-review":
        data.update(c.fingerprints(root, ["paper/sections", "paper/figures", "paper/refs.bib"]))
    return data

def state(root, run, template, override=None):
    nodes = graph(root, run, template)
    manifests = {q: load_manifest(root, q) for q in [*run["questions"], "GLOBAL"]}
    if override:
        manifests[override["question_id"]] = override
    valid, errors = {}, {}
    for key, step in nodes.items():
        rec = step_record(manifests[step["question_id"]], step["id"])
        deps_ok = all(valid[d] for d in step["dependencies"])
        try:
            matches = rec.get("snapshot") == snapshot(root, step, nodes)
        except (OSError, ValueError):
            matches = False
        valid[key] = rec.get("status") == "completed" and deps_ok and matches
        if rec.get("status") == "completed" and not valid[key]:
            errors[key] = "inputs, outputs, decision, or upstream evidence changed"
        elif not deps_ok:
            errors[key] = "waiting for dependencies: " + ", ".join(d for d in step["dependencies"] if not valid[d])
        elif rec.get("error"):
            errors[key] = str(rec["error"])
    return nodes, manifests, valid, errors

def action_for(root, run, nodes, valid, q=None):
    candidates = []
    for key, step in nodes.items():
        if valid[key] or (q and step["question_id"] not in {q, "GLOBAL"}):
            continue
        if not all(valid[d] for d in step["dependencies"]):
            continue
        display_question = step["question_id"] if step["question_id"] != "GLOBAL" or q else (run["questions"][0] if run["questions"] else "GLOBAL")
        candidates.append({"status": "READY", "question_id": display_question, "scope": step["question_id"], "node": key, "step": step["id"],
            "skill": step["skill"], "outputs": step["outputs"], "checks": step.get("checks", []),
            "owner": "human" if step.get("checkpoint") else "agent", "checkpoint": step.get("checkpoint"),
            "evidence_hashes": binding(root, step, nodes)})
    if candidates:
        return next((a for a in candidates if a["owner"] == "agent"), candidates[0])
    return {"status": "COMPLETE"} if all(valid.values()) else {"status": "BLOCKED", "reason": "unfinished dependencies; use next without --question"}

def derive_question(root, run, template, manifest):
    nodes, _, valid, errors = state(root, run, template, manifest)
    q, gate = manifest["question_id"], "G0"
    for key, step in nodes.items():
        if step["question_id"] in {q, "GLOBAL"} and valid[key]:
            candidate = step.get("gate_after", "G0")
            if GATE_ORDER[candidate] > GATE_ORDER[gate]:
                gate = candidate
    complete = all(valid.values())
    action = action_for(root, run, nodes, valid, q)
    manifest.update(current_gate="G6" if complete and run["profile"] == "submission" else min(gate, "G5", key=GATE_ORDER.get),
        status="completed" if complete else ("waiting_human" if action.get("owner") == "human" else action["status"].lower()),
        next_action=action if action["status"] == "READY" else None,
        blockers=[v for k, v in errors.items() if k.startswith(q + ":")])
    manifest["allowed"] = {"code_generation": valid.get(f"{q}:method-choice", False),
        "freeze": valid.get(f"{q}:result-verdict", False), "paper_writing": valid.get(f"{q}:freeze", False),
        "final_assembly": all(valid.get(f"{x}:paper-section", False) for x in run["questions"])}
    return manifest

def step_complete(root, manifest, step):
    if not runtime_paths(root)["run"].is_file():
        paths = [root / p for p in outputs_for(step, manifest["question_id"])]
        if not all(p.is_file() and p.stat().st_size for p in paths):
            return False
        if step.get("id") == "docx-export":
            files = sorted((root / "paper").rglob("*.tex"))
            snap = [(p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
            old = manifest.get("_compat_snapshot")
            manifest["_compat_snapshot"] = snap
            return old is None or old == snap
        return True
    run, template = load_runtime(root)
    return state(root, run, template, manifest)[2].get(f"{manifest['question_id']}:{step['id']}", False)

def resolved_config(root, args, session, template):
    config = {**template["defaults"], **session}
    for argument, key in {"contest": "contest_profile", "paper_format": "paper_format", "delivery_mode": "delivery_mode",
        "language": "implementation_language", "seed": "random_seed", "paper_language": "paper_language"}.items():
        value = getattr(args, argument, None)
        if value is not None:
            config[key] = value
    if config.get("implementation_language", "auto") == "auto":
        config["implementation_language"] = "matlab" if any((root / "code").rglob("*.m")) else "python"
    if config.get("paper_format") != "latex":
        config["delivery_mode"] = "single"
    for key, value in {"random_seed": 2026, "question_dependencies": {}, "research_budget_minutes": 30, "paper_reserve_minutes": 180}.items():
        config.setdefault(key, value)
    return config

def cmd_init(root, args):
    paths = runtime_paths(root)
    if paths["run"].exists():
        raise WorkflowError("workflow exists; use reconfigure or migrate")
    session = read_json(paths["session"]) if paths["session"].exists() else {}
    profile = getattr(args, "profile", None) or session.get("rigor_profile", "submission")
    template = load_template(profile)
    config = resolved_config(root, args, session, template)
    raw = getattr(args, "questions", None)
    questions = [normalize_question(q) for q in raw.split(",")] if raw else session.get("active_questions", ["Q1"])
    if len(set(questions)) != len(questions) or "GLOBAL" in questions or not questions:
        raise WorkflowError("invalid question list")
    if not git_context(root)["available"] and not getattr(args, "allow_no_git", False):
        raise WorkflowError("formal workflow requires Git")
    session.update(config, rigor_profile=profile, active_questions=questions)
    session.setdefault("schema_version", 1)
    session.setdefault("interaction_mode", "speed")
    run = {"schema_version": 1, "runtime_revision": RUNTIME_REVISION, "profile": profile, "questions": questions,
        "workflow_id": getattr(args, "workflow_id", None) or "math-modeling-session", "status": "running",
        "config": config, "session_hash": hash_value(session), "template_snapshot": template,
        "iterations": {q: "round1" for q in questions}, "created_at": now()}
    graph(root, run, template)
    write_json(paths["session"], session)
    write_json(paths["run"], run)
    for q in [*questions, "GLOBAL"]:
        save_manifest(root, initial_manifest(q, profile))
    write_json(paths["artifacts"], {"schema_version": 1, "items": []})
    record_event(root, "initialized", runtime_revision=RUNTIME_REVISION)
    return {"status": "INITIALIZED", "workflow": run, "next": cmd_next(root, argparse.Namespace(question=None))}

def cmd_next(root, args):
    run, template = load_runtime(root)
    if run["status"] == "paused":
        return {"status": "PAUSED", "reason": run.get("pause_reason")}
    nodes, _, valid, _ = state(root, run, template)
    result = action_for(root, run, nodes, valid, getattr(args, "question", None))
    deadline = run["config"].get("deadline_at")
    if deadline:
        remaining = (datetime.fromisoformat(deadline.replace("Z", "+00:00")) - datetime.now(timezone.utc)).total_seconds() / 60
        result["remaining_minutes"] = round(remaining, 1)
        if remaining <= run["config"]["paper_reserve_minutes"]:
            result["time_guidance"] = "protect paper time; finish minimum viable answers; defer optional experiments; never auto-approve"
    return result

def cmd_status(root, args):
    run, template = load_runtime(root)
    _, _, valid, errors = state(root, run, template)
    return {"status": "completed" if all(valid.values()) else ("paused" if run["status"] == "paused" else "running"),
        "profile": run["profile"], "questions": [derive_question(root, run, template, load_manifest(root, q)) for q in run["questions"]],
        "invalidated": errors, "next": cmd_next(root, args)}

def resolve_step(root, run, template, q, requested):
    nodes, manifests, valid, _ = state(root, run, template)
    action = action_for(root, run, nodes, valid, q)
    sid = requested or action.get("step")
    key = f"{q}:{sid}" if f"{q}:{sid}" in nodes else f"GLOBAL:{sid}"
    if key not in nodes or valid[key] or not all(valid[d] for d in nodes[key]["dependencies"]):
        raise WorkflowError(f"step is not ready: {key}")
    step = nodes[key]
    return manifests[step["question_id"]], step

def cmd_start(root, args):
    run, template = load_runtime(root)
    if run["status"] == "paused":
        raise WorkflowError("workflow paused")
    manifest, step = resolve_step(root, run, template, normalize_question(args.question), args.step)
    nodes = graph(root, run, template)
    step_record(manifest, step["id"]).update(status="running", started_at=now(), input_snapshot=binding(root, step, nodes), error=None)
    save_manifest(root, manifest)
    record_event(root, "started", question_id=step["question_id"], step=step["id"])
    return {"status": "RUNNING", "step": step["id"], "evidence_hashes": binding(root, step, nodes)}

def validate_step(root, manifest, step):
    run, template = load_runtime(root)
    nodes = graph(root, run, template)
    step = nodes.get(f"{manifest['question_id']}:{step['id']}", step)
    errors = c.execute(root, step, run["config"])
    if step.get("checkpoint"):
        decision = decision_for(root, step) or {}
        allowed = step["checkpoint"].get("choices")
        choice_ok = decision.get("choice") in allowed if allowed else bool(decision.get("choice"))
        if step["id"] == "method-choice":
            selected = decision.get("selected_method") or decision.get("choice")
            choice_ok = bool(selected) and selected not in {"accept", "reject", "adjust", "fallback"}
        if not choice_ok or not decision.get("decision_id") or not decision.get("user_message"):
            errors.append("missing typed human choice with decision_id and actual user_message")
        if decision.get("evidence_hashes") != binding(root, step, nodes):
            errors.append("human decision not bound to current evidence; use decision-context")
        if step["id"] == "result-verdict" and decision.get("experiment_id") != run["iterations"][step["question_id"]]:
            errors.append("verdict belongs to another experiment")
    return errors

def cmd_finish(root, args):
    run, template = load_runtime(root)
    if run["status"] == "paused":
        raise WorkflowError("workflow paused")
    manifest, step = resolve_step(root, run, template, normalize_question(args.question), args.step)
    record = step_record(manifest, step["id"])
    if record.get("status") != "running":
        raise WorkflowError("start before finish; file presence cannot complete a step")
    errors = validate_step(root, manifest, step)
    nodes = graph(root, run, template)
    if not step.get("checkpoint") and record.get("input_snapshot") != binding(root, step, nodes):
        errors.append("inputs changed during execution; restart step")
    if errors:
        record.update(status="failed", error=errors)
        save_manifest(root, manifest)
        raise WorkflowError("; ".join(errors))
    decision = decision_for(root, step)
    if decision and decision["choice"] in {"reject", "adjust", "fallback"}:
        target = decision.get("rerun_from") or ("method-screen" if decision["choice"] == "fallback" else "model-run")
        if target not in {"data-audit", "feature-engineering", "method-screen", "code-plan", "model-run"}:
            raise WorkflowError("invalid diagnostic rerun_from")
        record.update(status="rejected", decision_id=decision["decision_id"])
        save_manifest(root, manifest)
        record_event(root, "result_" + decision["choice"], decision=decision)
        result = cmd_rerun(root, argparse.Namespace(question=step["question_id"], from_step=target, new_experiment=True))
        result["git_action"] = "preserve rejected experiment; use Git decision command before implementing next iteration"
        return result
    record.update(status="completed", snapshot=snapshot(root, step, nodes), completed_at=now(), error=None)
    if step["id"] == "freeze":
        manifest["freeze_state"] = "frozen"
    save_manifest(root, manifest)
    index = read_json(runtime_paths(root)["artifacts"])
    key = f"{step['question_id']}:{step['id']}"
    index["items"] = [x for x in index["items"] if x.get("node") != key]
    index["items"].append({"node": key, "paths": step["outputs"], "fingerprints": record["snapshot"]})
    write_json(runtime_paths(root)["artifacts"], index)
    record_event(root, "completed", node=key)
    nxt = cmd_next(root, argparse.Namespace(question=None))
    run["status"] = "completed" if nxt["status"] == "COMPLETE" else "running"
    write_json(runtime_paths(root)["run"], run)
    return {"status": "COMPLETED", "step": step["id"], "next": nxt}

def cmd_rerun(root, args):
    run, template = load_runtime(root)
    nodes, manifests, _, _ = state(root, run, template)
    q = normalize_question(args.question)
    key = f"{q}:{args.from_step}"
    if key not in nodes:
        key = f"GLOBAL:{args.from_step}"
    if key not in nodes:
        raise WorkflowError("unknown active rerun step")
    diagnostic_root = key
    if getattr(args, "new_experiment", False):
        git_key = f"{q}:git-experiment"
        if git_key in nodes and list(nodes).index(key) > list(nodes).index(git_key):
            key = git_key
    affected = {key}
    for node, step in nodes.items():
        if any(d in affected for d in step["dependencies"]):
            affected.add(node)
    if getattr(args, "new_experiment", False):
        run["iterations"][q] = "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    for node in affected:
        step = nodes[node]
        manifest = manifests[step["question_id"]]
        rec = step_record(manifest, step["id"])
        if step["id"] == "freeze" and rec.get("status") == "completed":
            manifest["freeze_state"] = "thaw_required"
            record_event(root, "thaw", question_id=step["question_id"], cause=key)
        rec.update(status="stale", error=None, stale_since=now())
    for manifest in manifests.values():
        save_manifest(root, manifest)
    run["status"] = "running"
    write_json(runtime_paths(root)["run"], run)
    record_event(root, "rerun", rerun_root=key, diagnostic_root=diagnostic_root, affected=sorted(affected))
    return {"status": "STALE", "affected": sorted(affected), "next": cmd_next(root, argparse.Namespace(question=q))}

def cmd_pause(root, args):
    run, _ = load_runtime(root)
    run.update(status="paused", pause_reason=args.reason)
    write_json(runtime_paths(root)["run"], run)
    return {"status": "PAUSED"}

def cmd_resume(root, args):
    run, _ = load_runtime(root)
    run.update(status="running", pause_reason=None)
    write_json(runtime_paths(root)["run"], run)
    return {"status": "RUNNING"}

def cmd_check(root, args):
    run, template = load_runtime(root)
    nodes, _, valid, errors = state(root, run, template)
    changed = {k: v for k, v in errors.items() if "changed" in v}
    return {"status": "FAILED" if changed else "PASSED", "invalidated": changed, "node_count": len(nodes),
            "completed_nodes": sum(valid.values()), "scope": "structure_and_evidence_freshness"}

def cmd_reconfigure(root, args):
    paths = runtime_paths(root)
    run, session = read_json(paths["run"]), read_json(paths["session"])
    profile = session.get("rigor_profile", run["profile"])
    migrate = getattr(args, "command", "") == "migrate"
    template = load_template(profile) if migrate or profile != run["profile"] else run["template_snapshot"]
    backup = root / "planning/history" / ("migration-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json")
    write_json(backup, {"run": run, "manifests": [read_json(p) for p in paths["manifests"].glob("*.json")]})
    previous = run.get("config", {})
    config = resolved_config(root, argparse.Namespace(), session, template)
    run.update(runtime_revision=RUNTIME_REVISION, config=config, profile=profile, template_snapshot=template,
               session_hash=hash_value(session), status="running")
    run.setdefault("iterations", {q: "round1" for q in run["questions"]})
    graph(root, run, template)
    write_json(paths["run"], run)
    for q in [*run["questions"], "GLOBAL"]:
        if not manifest_path(root, q).exists():
            save_manifest(root, initial_manifest(q, profile))
    changed = {k for k in set(previous) | set(config) if previous.get(k) != config.get(k)}
    paper_only = changed <= {"paper_format", "delivery_mode", "paper_language", "research_budget_minutes", "paper_reserve_minutes", "deadline_at"}
    for q in run["questions"]:
        target = "paper-section" if paper_only and profile == "submission" and not migrate else "problem-parse"
        cmd_rerun(root, argparse.Namespace(question=q, from_step=target, new_experiment=False))
    record_event(root, "reconfigured", changed=sorted(changed), backup=str(backup))
    return {"status": "RECONFIGURED", "backup": str(backup), "next": cmd_next(root, argparse.Namespace(question=None))}

def cmd_compare(root, args):
    script = SKILL_DIR.parent / "git-experiment-manager/scripts/compare_experiments.py"
    command = [sys.executable, str(script), str(c.inside(root, args.left)), str(c.inside(root, args.right))]
    if args.output:
        command.extend(["--output", str(c.inside(root, args.output))])
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode not in {0, 2}:
        raise WorkflowError(proc.stdout or proc.stderr)
    return json.loads(proc.stdout)

def cmd_export(root, args):
    run, template = load_runtime(root)
    if not all(state(root, run, template)[2].values()):
        raise WorkflowError("export requires current completed workflow evidence")
    target = args.destination.resolve()
    if target.exists():
        raise WorkflowError("destination exists")
    overleaf = getattr(args, "overleaf", False)
    roots = ["paper"] if overleaf else ["planning", "methods", "code", "results", "robustness", "paper", "workspace"]
    excluded = {"data_raw", "raw", "__pycache__", ".git", ".venv", "cache"}
    files = [p for name in roots for p in (root / name).rglob("*") if p.is_file() and not excluded.intersection(p.relative_to(root).parts)
             and p.suffix not in {".aux", ".log", ".tmp", ".pyc"}]
    if overleaf:
        files = [p for p in files if p.suffix in {".tex", ".bib", ".cls", ".sty", ".png", ".jpg", ".pdf", ".eps"} and p.name != "main.pdf" and "exports" not in p.parts]
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as out:
        for p in files:
            out.write(p, p.relative_to(root / "paper" if overleaf else root).as_posix())
    return {"status": "EXPORTED", "destination": str(target), "files": len(files)}

def cmd_decision_context(root, args):
    run, template = load_runtime(root)
    _, step = resolve_step(root, run, template, normalize_question(args.question), args.step)
    return {"status": "READY", "step": step["id"], "checkpoint": step.get("checkpoint"),
            "experiment_id": run["iterations"].get(step["question_id"]), "evidence_hashes": binding(root, step, graph(root, run, template))}

def cmd_record_decision(root, args):
    """Capture an explicit user answer against current evidence, without inventing reasons."""
    run, template = load_runtime(root)
    _, step = resolve_step(root, run, template, normalize_question(args.question), args.step)
    checkpoint = step.get("checkpoint")
    if not checkpoint or not args.user_message.strip():
        raise WorkflowError("a ready checkpoint and actual user message are required")
    if step["id"] == "method-choice":
        if not args.selected_method:
            raise WorkflowError("record the method explicitly selected by the user")
    elif args.choice not in checkpoint.get("choices", []):
        raise WorkflowError("choice is not supported by this checkpoint")
    q = step["question_id"]
    path = root / render(checkpoint.get("decision_file", f"methods/{q}/{q.lower()}_decisions.jsonl"), q)
    previous = decision_for(root, step)
    row = {"schema_version": 1, "decision_id": f"{q}-{step['id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}",
           "decision_type": checkpoint["decision_type"], "status": "DECIDED", "decided_by": "human",
           "choice": args.choice, "user_message": args.user_message, "rationale": args.rationale,
           "selected_method": args.selected_method, "experiment_id": run["iterations"].get(q),
           "evidence_hashes": binding(root, step, graph(root, run, template)), "decided_at": now(),
           "supersedes": previous.get("decision_id") if previous else None}
    if args.rerun_from:
        row["rerun_from"] = args.rerun_from
    append_jsonl(path, row)
    return {"status": "RECORDED", "decision": row, "path": str(path)}

def smoke_test():
    from smoke_case import run_smoke
    return run_smoke()


def create_smoke_output(workspace, step, question):
    """Compatibility fixture for focused delivery-check tests; formal runtime never uses it."""
    for raw in outputs_for(step, question):
        path = workspace / raw
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            write_json(path, {"status": "passed", "schema_version": 1})
        elif path.suffix == ".docx":
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("word/document.xml", "<document/>")
        else:
            path.write_text("compatibility smoke fixture\n", encoding="utf-8")
    if step.get("id") == "docx-export":
        source = workspace / "paper/main.tex"
        source.parent.mkdir(parents=True, exist_ok=True)
        if not source.exists():
            source.write_text("fixture\n", encoding="utf-8")
        docx = workspace / "paper/exports/main.docx"
        docx.parent.mkdir(parents=True, exist_ok=True)
        if not docx.exists():
            with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("[Content_Types].xml", "<Types/>")
                archive.writestr("word/document.xml", "<document/>")
        write_json(workspace / "paper/docx_export_report.json", {"status": "passed", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source_bundle_sha256": "fixture", "output_sha256": hashlib.sha256(docx.read_bytes()).hexdigest()})
        write_json(workspace / "paper/docx_delivery_check.json", {"status": "passed"})

def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, default=Path.cwd())
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--profile", choices=("lean", "submission"))
    init.add_argument("--questions")
    init.add_argument("--contest")
    init.add_argument("--paper-format", choices=("latex", "word", "markdown", "none"))
    init.add_argument("--delivery-mode", choices=("single", "latex_primary_docx_mirror"))
    init.add_argument("--language", choices=("auto", "python", "matlab"))
    init.add_argument("--paper-language")
    init.add_argument("--workflow-id")
    init.add_argument("--seed", type=int)
    init.add_argument("--allow-no-git", action="store_true")
    for name in ("status", "next"):
        sub.add_parser(name).add_argument("--question")
    for name in ("start", "finish", "decision-context"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--question", required=True)
        cmd.add_argument("--step")
    decision = sub.add_parser("record-decision")
    decision.add_argument("--question", required=True)
    decision.add_argument("--step", required=True)
    decision.add_argument("--choice", required=True)
    decision.add_argument("--user-message", required=True)
    decision.add_argument("--rationale", default=None)
    decision.add_argument("--selected-method")
    decision.add_argument("--rerun-from", choices=("data-audit", "feature-engineering", "method-screen", "code-plan", "model-run"))
    sub.add_parser("pause").add_argument("--reason", required=True)
    for name in ("resume", "check", "migrate", "reconfigure", "smoke"):
        sub.add_parser(name)
    rerun = sub.add_parser("rerun")
    rerun.add_argument("--question", required=True)
    rerun.add_argument("--from-step", required=True)
    rerun.add_argument("--new-experiment", action="store_true")
    comp = sub.add_parser("compare")
    comp.add_argument("left")
    comp.add_argument("right")
    comp.add_argument("--output")
    export = sub.add_parser("export")
    export.add_argument("--destination", type=Path, required=True)
    export.add_argument("--overleaf", action="store_true")
    return p

def main():
    args = build_parser().parse_args()
    handlers = {name: globals()["cmd_" + name.replace("-", "_")] for name in (
        "init", "status", "next", "start", "finish", "pause", "resume", "rerun", "check", "compare", "export", "reconfigure", "decision-context", "record-decision")}
    handlers.update(migrate=cmd_reconfigure, smoke=lambda root, args: smoke_test())
    try:
        result = handlers[args.command](args.workspace.resolve(), args)
    except (OSError, ValueError, KeyError, WorkflowError, subprocess.SubprocessError) as exc:
        result = {"status": "FAILED", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result.get("status") == "FAILED" else 0

if __name__ == "__main__":
    sys.exit(main())
