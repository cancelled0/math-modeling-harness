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
RUNTIME_REVISION = 3

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
        produced = False
        for q in owners:
            step = copy.deepcopy(base)
            step["question_id"] = q
            if step.get("checkpoint", {}).get("conditional_field"):
                parse = root / "planning/problem_contract.json"
                field = step["checkpoint"]["conditional_field"]
                if not parse.is_file() or not read_json(parse).get(field):
                    continue
            key = f"{q}:{step['id']}"
            deps = set(filter(None, last.values())) if q == "GLOBAL" else ({last[q]} if last[q] else set())
            deps.update(render(x, q) for x in step.get("depends_on", []))
            if step["id"] == "method-screen":
                upstream_result = "result-verdict" if run["config"].get("require_result_verdict") else "result-synthesis"
                deps.update(f"{up}:{upstream_result}" for up in run["config"].get("question_dependencies", {}).get(q, []))
            iteration = run.get("iterations", {}).get(q, "round1")
            for field in ("outputs", "inputs"):
                step[field] = [render(x.replace("{experiment_id}", iteration), q) for x in step.get(field, [])]
            step["run_summary"] = f"results/{q}/experiments/{iteration}/run_summary.json"
            if step["id"] in {"implementation-spec", "model-run"} and run["config"].get("feature_engineering"):
                step["inputs"].extend([f"workspace/features/{q}/{q.lower()}_feature_spec.json", f"workspace/features/{q}/{q.lower()}_feature_audit.json"])
            if step["id"] == "model-run" and run["config"].get("detailed_code_plan"):
                base = "code/matlab" if run["config"].get("implementation_language") == "matlab" else "code"
                step["inputs"].append(f"{base}/{q}/{q.lower()}_implementation_spec.json")
            step["dependencies"] = sorted(deps)
            nodes[key] = step
            produced = True
        if produced:
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
    if step.get("delivery_artifact") or step["id"] in {"submission-audit", "quality-audit"}:
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

def derive_question(root, run, template, manifest, computed=None):
    nodes, _, valid, errors = computed or state(root, run, template, manifest)
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
    accepted_result = valid.get(f"{q}:result-verdict", False) if run["config"].get("require_result_verdict") else valid.get(f"{q}:result-synthesis", False)
    manifest["allowed"] = {"code_generation": valid.get(f"{q}:method-choice", False),
        "freeze": accepted_result, "paper_writing": valid.get(f"{q}:freeze", False),
        "final_assembly": all(valid.get(f"{x}:paper-section", False) for x in run["questions"])}
    return manifest


def read_json_optional(path):
    return read_json(path) if path.is_file() else None


def read_jsonl(path):
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkflowError(f"invalid JSONL record: {path}:{number}: {exc}") from exc
        if not isinstance(row, dict):
            raise WorkflowError(f"expected JSON object: {path}:{number}")
        rows.append(row)
    return rows


def compact_value(value, depth=0):
    """Bound cache size without interpreting or rewriting source evidence."""
    if depth >= 4:
        return "[truncated]"
    if isinstance(value, str):
        return value if len(value) <= 1200 else value[:1200] + "…"
    if isinstance(value, list):
        items = [compact_value(item, depth + 1) for item in value[:20]]
        if len(value) > 20:
            items.append({"omitted_items": len(value) - 20})
        return items
    if isinstance(value, dict):
        keys = sorted(value)[:30]
        result = {key: compact_value(value[key], depth + 1) for key in keys}
        if len(value) > 30:
            result["omitted_fields"] = len(value) - 30
        return result
    return value


def project_fields(value, fields):
    if not isinstance(value, dict):
        return None
    result = {key: compact_value(value[key]) for key in fields if key in value}
    return result or None


def direct_fingerprints(root, paths):
    """Hash only named context sources; workflow snapshots already bind transitive files."""
    result = {}
    for raw in sorted(set(paths)):
        path = c.inside(root, raw)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = c.digest(path)
    return result


def context_source_paths(run, q):
    iteration = run.get("iterations", {}).get(q, "round1")
    lower = q.lower()
    return [
        "planning/workflow_run.json",
        "planning/session_config.json",
        "planning/events.jsonl",
        "planning/experiment_registry.jsonl",
        "planning/framing_decisions.jsonl",
        "planning/problem_contract.json",
        "planning/manifests/GLOBAL.json",
        f"planning/manifests/{q}.json",
        f"planning/experiments/{q}/active_experiment.json",
        "workspace/data/data_profile.json",
        "workspace/data/source_registry.json",
        f"workspace/evidence/{q}/evidence_brief.json",
        f"workspace/features/{q}/{lower}_feature_spec.json",
        f"workspace/features/{q}/{lower}_feature_audit.json",
        f"methods/{q}/method_contract.json",
        f"methods/{q}/{lower}_foundations.json",
        f"methods/{q}/{lower}_decisions.jsonl",
        f"results/{q}/experiments/{iteration}/run_summary.json",
        f"results/{q}/reports/{lower}_run_assessment.json",
        f"results/{q}/reports/{lower}_result_evidence.json",
        f"results/{q}/reports/frozen_numbers.json",
        f"robustness/{q}/{lower}_robustness_summary.json",
    ]


def source_as_of(root, paths):
    timestamps = []

    def collect(value, key=""):
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect(child, child_key)
        elif isinstance(value, list):
            for child in value:
                collect(child, key)
        elif isinstance(value, str) and (key.endswith("_at") or key in {"recorded_at", "decided_at"}):
            timestamps.append(value)

    for raw in paths:
        path = c.inside(root, raw)
        if not path.is_file():
            continue
        if path.suffix == ".jsonl":
            for row in read_jsonl(path):
                collect(row)
        elif path.suffix == ".json":
            collect(read_json(path))
    return max(timestamps) if timestamps else None


def find_subquestion(problem, q):
    if not isinstance(problem, dict):
        return None
    rows = problem.get("subquestions", [])
    if isinstance(rows, dict):
        value = rows.get(q)
        return value if isinstance(value, dict) else ({"id": q, "classification": value} if value is not None else None)
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and str(row.get("id", "")).upper() == q:
            return row
        if isinstance(row, str) and row.upper() == q:
            return {"id": q}
    return None


def normalized_findings(value, source, kind, default_scope=None):
    rows = value if isinstance(value, list) else ([value] if value not in (None, {}, []) else [])
    result = []
    for row in rows[:20]:
        if isinstance(row, dict):
            text_value = row.get("text", row.get("claim", row.get("statement", row)))
            scope = row.get("scope", default_scope)
            evidence = {key: row[key] for key in ("result_labels", "derivation_ids", "source_file", "source_locator") if key in row}
        else:
            text_value, scope, evidence = row, default_scope, {}
        result.append({"kind": kind, "text": compact_value(text_value), "scope": compact_value(scope),
                       "evidence": compact_value(evidence), "source": source})
    return result


def decision_context_summary(root, run, nodes, valid, q):
    confirmed, stale = [], []
    seen = set()
    for key, step in nodes.items():
        if step["question_id"] not in {q, "GLOBAL"} or not step.get("checkpoint"):
            continue
        checkpoint = step["checkpoint"]
        identity = (step["question_id"], checkpoint["decision_type"])
        if identity in seen:
            continue
        seen.add(identity)
        owner = step["question_id"]
        path_raw = render(checkpoint.get("decision_file", f"methods/{owner}/{owner.lower()}_decisions.jsonl"), owner)
        row = latest_decision(root / path_raw, checkpoint["decision_type"])
        if not row:
            continue
        deps_current = all(valid.get(dep, False) for dep in step["dependencies"])
        evidence_current = row.get("evidence_hashes") == binding(root, step, nodes) and deps_current
        item = project_fields(row, ("decision_id", "decision_type", "decided_by", "choice", "selected_method", "user_message",
                                    "rationale", "experiment_id", "decided_at", "supersedes")) or {}
        item.update(scope=owner, source=path_raw, evidence_current=evidence_current)
        if evidence_current:
            confirmed.append(item)
        else:
            stale.append({"kind": "human_decision", "reason": "evidence_or_dependencies_changed", **item})
    return confirmed, stale


def experiment_summary(root, run, q):
    iteration = run.get("iterations", {}).get(q, "round1")
    active_raw = f"planning/experiments/{q}/active_experiment.json"
    summary_raw = f"results/{q}/experiments/{iteration}/run_summary.json"
    active = read_json_optional(root / active_raw)
    summary = read_json_optional(root / summary_raw)
    registry = read_jsonl(runtime_paths(root)["experiments"])
    relevant = []
    for row in registry:
        branch_name = str(row.get("branch", "")).lower()
        if str(row.get("question_id", "")).upper() == q or row.get("experiment_id") == iteration or f"/{q.lower()}/" in branch_name:
            relevant.append(row)
    lifecycle = next((row for row in reversed(relevant) if row.get("experiment_id") == iteration or not row.get("experiment_id")), None)
    return {
        "experiment_id": iteration,
        "lifecycle_status": lifecycle.get("event") if lifecycle else (active.get("status") if active else "not_started"),
        "active_context_source": active_raw if active else None,
        "active_context": project_fields(active, ("status", "algorithm", "branch", "base_branch", "parent_commit",
                                                   "experiment_id", "question_id", "started_at")),
        "run_summary_source": summary_raw if summary else None,
        "run": project_fields(summary, ("status", "task_type", "primary_metric", "comparison_contract", "methods",
                                           "random_seed", "execution", "environment", "runtime_seconds", "fallback_trigger")),
        "latest_registry_event": compact_value(lifecycle) if lifecycle else None,
    }, relevant


def build_active_context(root, run, template, q, computed=None):
    if q not in run["questions"]:
        raise WorkflowError(f"question is not active: {q}")
    nodes, manifests, valid, errors = computed or state(root, run, template)
    question_state = derive_question(root, run, template, manifests[q], (nodes, manifests, valid, errors))
    paths = context_source_paths(run, q)
    problem = read_json_optional(root / "planning/problem_contract.json")
    subquestion = find_subquestion(problem, q)
    data_profile = read_json_optional(root / "workspace/data/data_profile.json")
    evidence_raw = f"workspace/evidence/{q}/evidence_brief.json"
    academic_evidence = read_json_optional(root / evidence_raw)
    feature_spec_raw = f"workspace/features/{q}/{q.lower()}_feature_spec.json"
    feature_audit_raw = f"workspace/features/{q}/{q.lower()}_feature_audit.json"
    feature_spec = read_json_optional(root / feature_spec_raw)
    feature_audit = read_json_optional(root / feature_audit_raw)
    method_raw = f"methods/{q}/method_contract.json"
    method = read_json_optional(root / method_raw)
    foundations_raw = f"methods/{q}/{q.lower()}_foundations.json"
    foundations = read_json_optional(root / foundations_raw)
    assessment_raw = f"results/{q}/reports/{q.lower()}_run_assessment.json"
    assessment = read_json_optional(root / assessment_raw)
    result_raw = f"results/{q}/reports/{q.lower()}_result_evidence.json"
    result_evidence = read_json_optional(root / result_raw)
    robustness_raw = f"robustness/{q}/{q.lower()}_robustness_summary.json"
    robustness = read_json_optional(root / robustness_raw)
    freeze_raw = f"results/{q}/reports/frozen_numbers.json"
    frozen = read_json_optional(root / freeze_raw)
    confirmed, stale_decisions = decision_context_summary(root, run, nodes, valid, q)
    experiment, registry_rows = experiment_summary(root, run, q)

    if run["status"] == "paused":
        next_action = {"status": "PAUSED", "reason": run.get("pause_reason")}
    else:
        next_action = question_state.get("next_action") or ({"status": "COMPLETE"} if question_state["status"] == "completed"
                                                               else {"status": "BLOCKED", "reason": "no ready action"})
    current_step = next_action.get("step")
    if current_step:
        owner = next_action.get("scope", q)
        rec = manifests[owner].get("steps", {}).get(current_step, {})
        current_step = {"id": current_step, "skill": next_action.get("skill"), "owner": next_action.get("owner"),
                        "status": rec.get("status", "ready")}

    accepted_result = (valid.get(f"{q}:result-verdict", False) if run["config"].get("require_result_verdict")
                       else valid.get(f"{q}:result-synthesis", False))
    robustness_current = valid.get(f"{q}:robustness", False)
    freeze_current = valid.get(f"{q}:freeze", False)
    supported = []
    hypotheses = []
    if result_evidence:
        result_findings = normalized_findings(result_evidence.get("results"), result_raw, "model_result",
                                              result_evidence.get("claim_scope"))
        (supported if accepted_result else hypotheses).extend(result_findings)
    if robustness and robustness_current:
        supported.extend(normalized_findings(robustness.get("findings"), robustness_raw, "robustness",
                                             "current experiment and tested perturbations"))
    if frozen and freeze_current:
        claims = frozen.get("claims", frozen.get("frozen_numbers", frozen.get("items", [])))
        supported.extend(normalized_findings(claims, freeze_raw, "frozen_claim", "approved claim scope"))
    if subquestion:
        hypotheses.extend(normalized_findings(subquestion.get("proposed_relationships"),
                                              "planning/problem_contract.json", "proposed_relationship"))
    if foundations:
        hypotheses.extend(normalized_findings(foundations.get("assumptions"), foundations_raw, "model_assumption"))

    stale_items = list(stale_decisions)
    for key, step in nodes.items():
        if step["question_id"] not in {q, "GLOBAL"}:
            continue
        rec = manifests[step["question_id"]].get("steps", {}).get(step["id"], {})
        if rec.get("status") in {"stale", "rejected", "failed"} or (rec.get("status") == "completed" and not valid[key]):
            stale_items.append({"kind": "workflow_step", "node": key, "status": rec.get("status"),
                                "reason": errors.get(key, rec.get("error"))})
    for row in registry_rows:
        if row.get("event") == "experiment_rejected":
            stale_items.append({"kind": "experiment", "status": "rejected", "reason": "human_result_verdict",
                                "experiment_id": row.get("experiment_id"), "branch": row.get("branch"),
                                "source": "planning/experiment_registry.jsonl"})

    blockers = []
    if next_action.get("status") == "PAUSED":
        blockers.append({"kind": "paused", "reason": next_action.get("reason")})
    elif next_action.get("status") == "BLOCKED":
        blockers.append({"kind": "dependency", "reason": next_action.get("reason")})
    elif next_action.get("owner") == "human":
        blockers.append({"kind": "human_checkpoint", "reason": next_action.get("checkpoint", {}).get("reason")})

    methods = project_fields(method, ("main", "reference_policy", "conditional_fallback", "fallback", "rationale",
                                             "task_type", "required_checks"))
    selected_method = next((row.get("selected_method") for row in reversed(confirmed)
                            if row.get("decision_type") == "method_choice" and row.get("selected_method")), None)
    payload = {
        "context_schema_version": 1,
        "canonicality": {"role": "derived_cache", "authoritative_sources_override": True,
                         "regenerate_with": f"workflow.py --workspace <workspace> context --question {q}"},
        "workflow": {
            "workflow_id": run.get("workflow_id"), "profile": run["profile"], "contest_profile": run["config"].get("contest_profile"),
            "implementation_language": run["config"].get("implementation_language"), "paper_format": run["config"].get("paper_format"),
            "delivery_mode": run["config"].get("delivery_mode"), "question_id": q, "gate": question_state.get("current_gate"),
            "status": question_state.get("status"), "run_status": run.get("status"), "current_step": current_step,
        },
        "problem": {
            "source": "planning/problem_contract.json" if problem else None,
            "global_goal": compact_value(problem.get("global_goal")) if problem else None,
            "question": project_fields(subquestion, ("id", "statement", "goal", "required_outputs", "success_criteria", "constraints", "dependencies")),
            "classification": project_fields(subquestion, ("primary_type", "secondary_type", "confidence", "required_validation", "risks")),
        },
        "confirmed_decisions": confirmed,
        "methods": {"source": method_raw if method else None, "selected_method": selected_method, "contract": methods},
        "data": {"source": "workspace/data/data_profile.json" if data_profile else None,
                 "profile": project_fields(data_profile, ("status", "data_mode", "input_files", "quality_findings", "no_data_reason", "warnings", "limitations"))},
        "academic_evidence": {"source": evidence_raw if academic_evidence else None,
                              "brief": project_fields(academic_evidence, ("status", "findings", "gaps", "stop_reason", "limitations")),
                              "search_count": len(academic_evidence.get("search_log", [])) if academic_evidence else 0},
        "features": {
            "spec_source": feature_spec_raw if feature_spec else None,
            "spec": project_fields(feature_spec, ("question_id", "target", "split_contract", "fit_scope", "features", "transform_pipeline", "units", "output_columns")),
            "audit_source": feature_audit_raw if feature_audit else None,
            "audit": project_fields(feature_audit, ("status", "decisions", "leakage_checks", "ablation_results", "stability", "limitations", "review_status")),
        },
        "active_experiment": experiment,
        "run_assessment": {"source": assessment_raw if assessment else None,
                           "assessment": project_fields(assessment, ("status", "findings", "risk_disposition", "rerun_from"))},
        "supported_findings": supported,
        "hypotheses": hypotheses,
        "stale_or_rejected": stale_items,
        "blockers": blockers,
        "next_action": compact_value(next_action),
        "source_sha256": direct_fingerprints(root, paths),
    }
    payload["generated"] = {"renderer": "workflow-orchestrator/context-v1", "as_of": source_as_of(root, paths),
                            "state_sha256": hash_value(payload)}
    return payload


def markdown_scalar(value, limit=1200):
    if value in (None, "", [], {}):
        return "尚无"
    if isinstance(value, str):
        encoded = value
    else:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return encoded if len(encoded) <= limit else encoded[:limit] + "…（完整字段见 JSON 索引）"


def render_active_context(data):
    workflow = data["workflow"]
    problem = data["problem"]
    lines = [f"# {workflow['question_id']} 活动上下文", "",
             "> 这是可重建索引；与权威文件冲突时，以权威文件为准。", "",
             "## 当前状态", "",
             f"- 流程：`{workflow.get('profile')}`；阶段门：`{workflow.get('gate')}`；状态：`{workflow.get('status')}`",
             f"- 当前步骤：{markdown_scalar(workflow.get('current_step'))}",
             f"- 状态哈希：`{data['generated']['state_sha256']}`", "",
             "## 题目契约", "",
             f"- 总目标：{markdown_scalar(problem.get('global_goal'))}",
             f"- 本问：{markdown_scalar(problem.get('question'))}", "",
             "## 学术证据", "", markdown_scalar(data["academic_evidence"]), "",
             "## 已确认的人工决定", ""]
    if data["confirmed_decisions"]:
        for row in data["confirmed_decisions"]:
            lines.append(f"- `{row.get('decision_type')}` / `{row.get('decision_id')}`：{row.get('user_message')}（选择：{row.get('selected_method') or row.get('choice')}）")
    else:
        lines.append("- 尚无与当前证据绑定的人工决定。")
    lines.extend(["", "## 方法、数据与特征", "",
                  f"- 方法：{markdown_scalar(data['methods'])}",
                  f"- 数据：{markdown_scalar(data['data'])}",
                  f"- 特征：{markdown_scalar(data['features'])}", "",
                  "## 当前实验", "", markdown_scalar(data["active_experiment"]), "",
                  "## 已支持的结论", ""])
    findings = data["supported_findings"]
    lines.extend([f"- {markdown_scalar(row, 700)}" for row in findings[:8]] or ["- 尚无已接受或已验证的结论。"])
    if len(findings) > 8:
        lines.append(f"- 其余 {len(findings) - 8} 项见 JSON 索引。")
    lines.extend(["", "## 待验证假设", ""])
    hypotheses = data["hypotheses"]
    lines.extend([f"- {markdown_scalar(row, 700)}" for row in hypotheses[:8]] or ["- 尚无。"])
    if len(hypotheses) > 8:
        lines.append(f"- 其余 {len(hypotheses) - 8} 项见 JSON 索引。")
    lines.extend(["", "## 失效或已拒绝内容", ""])
    stale = data["stale_or_rejected"]
    lines.extend([f"- {markdown_scalar(row, 700)}" for row in stale[:12]] or ["- 尚无。"])
    if len(stale) > 12:
        lines.append(f"- 其余 {len(stale) - 12} 项见 JSON 索引。")
    lines.extend(["", "## 阻塞项与唯一下一动作", "",
                  f"- 阻塞项：{markdown_scalar(data['blockers'])}",
                  f"- 下一动作：{markdown_scalar(data['next_action'])}", "",
                  "## 权威来源哈希", "", "| 文件 | SHA256 |", "|---|---|"])
    lines.extend(f"| `{path}` | `{digest}` |" for path, digest in data["source_sha256"].items())
    return "\n".join(lines).rstrip() + "\n"


def write_active_context(root, run, template, q, output_format="both", computed=None):
    data = build_active_context(root, run, template, q, computed)
    folder = root / "planning/context"
    json_path = folder / f"{q}_active_context.json"
    md_path = folder / f"{q}_active_context.md"
    written = []
    if output_format in {"json", "both"}:
        encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if not json_path.is_file() or json_path.read_text(encoding="utf-8") != encoded:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            temp = json_path.with_suffix(json_path.suffix + ".tmp")
            temp.write_text(encoded, encoding="utf-8")
            os.replace(temp, json_path)
        written.append(json_path.relative_to(root).as_posix())
    if output_format in {"md", "both"}:
        rendered = render_active_context(data)
        if not md_path.is_file() or md_path.read_text(encoding="utf-8") != rendered:
            md_path.parent.mkdir(parents=True, exist_ok=True)
            temp = md_path.with_suffix(md_path.suffix + ".tmp")
            temp.write_text(rendered, encoding="utf-8")
            os.replace(temp, md_path)
        written.append(md_path.relative_to(root).as_posix())
    return {"question_id": q, "state_sha256": data["generated"]["state_sha256"], "artifacts": written}


def refresh_active_contexts(root, run, template, questions=None, output_format="both", computed=None):
    refreshed, errors = [], []
    computed = computed or state(root, run, template)
    for q in questions or run["questions"]:
        try:
            refreshed.append(write_active_context(root, run, template, q, output_format, computed))
        except (OSError, ValueError, KeyError, WorkflowError) as exc:
            errors.append({"question_id": q, "error": str(exc)})
    return {"status": "PASSED" if not errors else "FAILED", "contexts": refreshed, "errors": errors}


def cmd_context(root, args):
    run, template = load_runtime(root)
    questions = run["questions"] if getattr(args, "all", False) else [normalize_question(args.question)]
    result = refresh_active_contexts(root, run, template, questions, args.format)
    if result["errors"]:
        raise WorkflowError("; ".join(f"{row['question_id']}: {row['error']}" for row in result["errors"]))
    result["status"] = "GENERATED"
    return result

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
    raw_question = getattr(args, "question", None)
    question = normalize_question(raw_question) if raw_question else None
    refresh_questions = [question] if question else run["questions"]
    if run["status"] == "paused":
        result = {"status": "PAUSED", "reason": run.get("pause_reason")}
        result["context_refresh"] = refresh_active_contexts(root, run, template, refresh_questions)
        return result
    computed = state(root, run, template)
    nodes, _, valid, _ = computed
    result = action_for(root, run, nodes, valid, question)
    deadline = run["config"].get("deadline_at")
    if deadline:
        remaining = (datetime.fromisoformat(deadline.replace("Z", "+00:00")) - datetime.now(timezone.utc)).total_seconds() / 60
        result["remaining_minutes"] = round(remaining, 1)
        if remaining <= run["config"]["paper_reserve_minutes"]:
            result["time_guidance"] = "protect paper time; finish minimum viable answers; defer optional experiments; never auto-approve"
    result["context_refresh"] = refresh_active_contexts(root, run, template, refresh_questions, computed=computed)
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
    questions = run["questions"] if step["question_id"] == "GLOBAL" else [step["question_id"]]
    return {"status": "RUNNING", "step": step["id"], "evidence_hashes": binding(root, step, nodes),
            "context_refresh": refresh_active_contexts(root, run, template, questions)}

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
    if step["id"] == "run-assessment":
        assessment = read_json(root / step["outputs"][0])
        if assessment.get("status") == "needs_repair":
            target = assessment.get("rerun_from")
            allowed = {"data-audit", "feature-engineering", "method-screen", "implementation-spec", "model-run", "code-review"}
            if target not in allowed:
                raise WorkflowError("repair assessment has invalid rerun_from")
            structural = target in {"data-audit", "feature-engineering", "method-screen"}
            record.update(status="diagnosed", error=None, completed_at=now())
            save_manifest(root, manifest)
            record_event(root, "run_needs_repair", question_id=step["question_id"], assessment=assessment)
            return cmd_rerun(root, argparse.Namespace(
                question=step["question_id"], from_step=target,
                new_run=True, new_branch=structural, new_experiment=False,
            ))
    decision = decision_for(root, step)
    if decision and decision["choice"] in {"reject", "adjust", "fallback"}:
        target = decision.get("rerun_from") or ("model-run" if decision["choice"] == "adjust" else "method-screen")
        if target not in {"data-audit", "feature-engineering", "method-screen", "implementation-spec", "model-run", "code-review"}:
            raise WorkflowError("invalid diagnostic rerun_from")
        structural = target in {"data-audit", "feature-engineering", "method-screen"}
        record.update(status="rejected", decision_id=decision["decision_id"])
        save_manifest(root, manifest)
        record_event(root, "result_" + decision["choice"], decision=decision)
        result = cmd_rerun(root, argparse.Namespace(
            question=step["question_id"], from_step=target,
            new_run=True, new_branch=structural, new_experiment=False,
        ))
        result["git_action"] = ("start a successor method-family branch after the new method decision" if structural
                                else "keep the approved method-family branch and record a new run")
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
    questions = run["questions"] if step["question_id"] == "GLOBAL" else [step["question_id"]]
    return {"status": "COMPLETED", "step": step["id"], "next": nxt,
            "context_refresh": refresh_active_contexts(root, run, template, questions)}

def cmd_rerun(root, args):
    run, template = load_runtime(root)
    q = normalize_question(args.question)
    initial_nodes = graph(root, run, template)
    key = f"{q}:{args.from_step}"
    if key not in initial_nodes:
        key = f"GLOBAL:{args.from_step}"
    if key not in initial_nodes:
        raise WorkflowError("unknown active rerun step")
    diagnostic_root = key
    new_run = bool(getattr(args, "new_run", False) or getattr(args, "new_experiment", False))
    new_branch = bool(getattr(args, "new_branch", False))
    if new_run or new_branch:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        owners = run["questions"] if key.startswith("GLOBAL:") else [q]
        for owner in owners:
            run["iterations"][owner] = "run-" + stamp
        write_json(runtime_paths(root)["run"], run)
    nodes, manifests, _, _ = state(root, run, template)
    if new_branch:
        git_key = f"{q}:git-experiment"
        if git_key in nodes and list(nodes).index(key) > list(nodes).index(git_key):
            key = git_key
    affected = {key}
    for node, step in nodes.items():
        if any(d in affected for d in step["dependencies"]):
            affected.add(node)
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
    record_event(root, "rerun", rerun_root=key, diagnostic_root=diagnostic_root, affected=sorted(affected),
                 new_run=new_run, new_branch=new_branch)
    return {"status": "STALE", "affected": sorted(affected), "run_id": run["iterations"].get(q),
            "new_branch_required": new_branch,
            "next": cmd_next(root, argparse.Namespace(question=q))}

def cmd_pause(root, args):
    run, template = load_runtime(root)
    run.update(status="paused", pause_reason=args.reason)
    write_json(runtime_paths(root)["run"], run)
    record_event(root, "paused", reason=args.reason)
    return {"status": "PAUSED", "reason": args.reason,
            "context_refresh": refresh_active_contexts(root, run, template)}

def cmd_resume(root, args):
    run, template = load_runtime(root)
    run.update(status="running", pause_reason=None)
    write_json(runtime_paths(root)["run"], run)
    record_event(root, "resumed")
    return {"status": "RUNNING", "context_refresh": refresh_active_contexts(root, run, template)}

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
        target = "paper-section" if paper_only and profile == "submission" and not migrate else "problem-frame"
        cmd_rerun(root, argparse.Namespace(question=q, from_step=target, new_run=False, new_branch=False, new_experiment=False))
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
           "decision_type": checkpoint["decision_type"], "question_id": q, "status": "DECIDED", "decided_by": "human",
           "choice": args.choice, "user_message": args.user_message, "rationale": args.rationale,
           "selected_method": args.selected_method, "experiment_id": run["iterations"].get(q),
           "evidence_hashes": binding(root, step, graph(root, run, template)), "decided_at": now(),
           "supersedes": previous.get("decision_id") if previous else None}
    if args.rerun_from:
        row["rerun_from"] = args.rerun_from
    append_jsonl(path, row)
    record_event(root, "decision_recorded", question_id=q, step=step["id"], decision_id=row["decision_id"])
    questions = run["questions"] if q == "GLOBAL" else [q]
    return {"status": "RECORDED", "decision": row, "path": str(path),
            "context_refresh": refresh_active_contexts(root, run, template, questions)}

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
    context = sub.add_parser("context")
    target = context.add_mutually_exclusive_group(required=True)
    target.add_argument("--question")
    target.add_argument("--all", action="store_true")
    context.add_argument("--format", choices=("json", "md", "both"), default="both")
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
    decision.add_argument("--rerun-from", choices=("data-audit", "feature-engineering", "method-screen", "implementation-spec", "model-run", "code-review"))
    sub.add_parser("pause").add_argument("--reason", required=True)
    for name in ("resume", "check", "migrate", "reconfigure", "smoke"):
        sub.add_parser(name)
    rerun = sub.add_parser("rerun")
    rerun.add_argument("--question", required=True)
    rerun.add_argument("--from-step", required=True)
    rerun.add_argument("--new-run", action="store_true", help="record a fresh run id on the current method-family branch")
    rerun.add_argument("--new-branch", action="store_true", help="invalidate the structural method-family branch context")
    rerun.add_argument("--new-experiment", action="store_true", help=argparse.SUPPRESS)
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
        "init", "status", "next", "context", "start", "finish", "pause", "resume", "rerun", "check", "compare", "export", "reconfigure", "decision-context", "record-decision")}
    handlers.update(migrate=cmd_reconfigure, smoke=lambda root, args: smoke_test())
    try:
        result = handlers[args.command](args.workspace.resolve(), args)
    except (OSError, ValueError, KeyError, WorkflowError, subprocess.SubprocessError) as exc:
        result = {"status": "FAILED", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result.get("status") == "FAILED" else 0

if __name__ == "__main__":
    sys.exit(main())
