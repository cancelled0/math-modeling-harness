"""Executable artifact contracts. A report is evidence, not an automatic approval."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from scientific_evidence import verify as verify_scientific_evidence
from pathlib import Path

CHECKS = Path(__file__).parent / "checks"
ARTIFACT_CONTRACTS = Path(__file__).parents[1] / "assets" / "artifact-contracts.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(root, raw):
    path = (root / raw).resolve()
    path.relative_to(root.resolve())
    return path


def load(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def referenced_files(value):
    """Only explicit file fields, never guess a URL or a model name is a path."""
    result = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"source_file", "local_path", "result_file", "run_summary", "receipt_file", "evaluation_audit_file", "constraint_audit_file"} and isinstance(item, str):
                result.append(item)
            elif key in {"input_files", "output_files", "evidence_files"} and isinstance(item, list):
                result.extend(x for x in item if isinstance(x, str))
            elif key == "files" and isinstance(item, dict):
                result.extend(x for x in item if isinstance(x, str))
            result.extend(referenced_files(item))
    elif isinstance(value, list):
        for item in value:
            result.extend(referenced_files(item))
    return result


def fingerprints(root, paths):
    """Hash declared files and transitive explicit JSON references, including missing files."""
    found = {}
    pending = list(paths)
    while pending:
        raw = pending.pop()
        path = inside(root, raw)
        name = path.relative_to(root).as_posix()
        if name in found:
            continue
        if path.is_dir():
            found[name + "/"] = "directory"
            pending.extend(p.relative_to(root).as_posix() for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            found[name] = digest(path)
            if path.suffix == ".json":
                pending.extend(referenced_files(json.loads(path.read_text(encoding="utf-8-sig"))))
        else:
            found[name] = None
    return dict(sorted(found.items()))


def artifact_errors(root, paths):
    errors = []
    for raw in paths:
        path = inside(root, raw)
        if not path.is_file() or not path.stat().st_size:
            errors.append(f"missing/empty artifact: {raw}")
            continue
        if path.suffix == ".json":
            try:
                data = load(path)
                if not data or str(data.get("status", "")).lower() in {
                    "failed", "error", "unavailable", "pending", "smoke", "blocked"
                }:
                    errors.append(f"unaccepted report: {raw}")
                if data.get("errors") or data.get("leakage_detected") is True:
                    errors.append(f"report contains errors: {raw}")
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
    return errors


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def artifact_contract_errors(step_id, outputs, root):
    """Validate the canonical lightweight field contract shared by producers and runtime."""
    spec = load(ARTIFACT_CONTRACTS).get("contracts", {}).get(step_id, [])
    errors = []
    for artifact in spec:
        index = artifact.get("output_index", 0)
        if index >= len(outputs):
            errors.append(f"{step_id} contract points outside declared outputs: {index}")
            continue
        raw = outputs[index]
        try:
            data = load(inside(root, raw))
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        for key in artifact.get("required", []):
            if key not in data:
                errors.append(f"{step_id} missing required field: {key}")
        for key in artifact.get("nonempty", []):
            if data.get(key) in (None, "", [], {}):
                errors.append(f"{step_id} requires nonempty field: {key}")
        for key, choices in artifact.get("allowed_values", {}).items():
            if key in data and data[key] not in choices:
                errors.append(f"{step_id} has invalid {key}: {data[key]}")
        for alternatives in artifact.get("one_of", []):
            if not any(data.get(key) not in (None, "", [], {}) for key in alternatives):
                errors.append(f"{step_id} requires one of: {', '.join(alternatives)}")
        for condition in artifact.get("conditional", []):
            if condition == "input_files_or_no_data_reason" and not data.get("input_files") and not data.get("no_data_reason"):
                errors.append("no-data task must explain no_data_reason")
            elif condition == "items_or_omission_reason" and not data.get("items") and not data.get("omission_reason"):
                errors.append("empty figure plan must explain omission_reason")
            elif condition == "figures_or_omission_reason" and not data.get("figures") and not data.get("omission_reason"):
                errors.append("empty figure manifest must explain omission_reason")
        if step_id == "run-assessment" and data.get("status") == "needs_repair" and not data.get("rerun_from"):
            errors.append("repair assessment must declare rerun_from")
    return errors


def evidence_errors(root, data):
    errors = []
    if not isinstance(data.get("search_log"), list) or not data["search_log"]:
        errors.append("evidence scan requires a search_log (query, provider, searched_at, outcome)")
    for row in data.get("search_log", []):
        if not all(row.get(k) for k in ("query", "provider", "searched_at", "outcome")):
            errors.append("incomplete search provenance")
    if not data.get("stop_reason") or "gaps" not in data:
        errors.append("evidence scan must record stop_reason and gaps, including empty gaps")
    for item in data.get("findings", []):
        if not all(item.get(k) for k in ("claim", "url", "access_level", "locator", "applicability", "limitations")):
            errors.append("finding lacks claim/source/access/locator/applicability/limitations")
        if item.get("access_level") not in {"metadata", "abstract", "fulltext"}:
            errors.append("invalid evidence access_level")
        if item.get("source_tier") == "contest_solution" and item.get("use") != "inspiration_only":
            errors.append("contest solution must be inspiration_only")
    return errors


def scientific_errors(root, data):
    errors = []
    if data.get("status") not in {"PASSED", "success", "passed"}:
        errors.append("run must be successful")
    if data.get("feasible") is False:
        errors.append("run is infeasible")
    metric = data.get("primary_metric")
    if metric is not None and (not isinstance(metric, dict) or not finite_number(metric.get("value"))):
        errors.append("primary metric must be finite when a scalar metric is declared")
    if metric is None and data.get("primary_result") in (None, "", [], {}):
        errors.append("run lacks a primary result")
    if not data.get("execution", {}).get("code_commit") or not data.get("environment") or "random_seed" not in data:
        errors.append("run lacks executed commit, environment or seed")
    receipt_raw = data.get("execution", {}).get("receipt_file")
    if not receipt_raw:
        errors.append("run lacks execution receipt")
    else:
        try:
            receipt = load(inside(root, receipt_raw))
            if receipt.get("exit_code") != 0 or receipt.get("status") != "success" or receipt.get("code_commit") != data["execution"]["code_commit"] or receipt.get("experiment_id") != data.get("experiment_id"):
                errors.append("execution receipt is inconsistent")
            for raw, expected in receipt.get("files", {}).items():
                if digest(inside(root, raw)) != expected:
                    errors.append(f"executed file changed: {raw}")
        except (OSError, ValueError):
            errors.append("execution receipt is missing or invalid")
    task = data.get("task_type")
    required = {
        "forecasting": ["temporal_split", "availability_time"],
        "time_series": ["temporal_split", "availability_time"],
        "optimization": ["feasibility", "constraint_residuals", "solver_status"],
        "mechanistic": ["units", "identifiability"],
        "evaluation": ["weight_sensitivity"],
        "regression": ["heldout_evaluation"],
        "classification": ["heldout_evaluation"],
        "simulation": ["replication_stability"],
    }.get(task)
    if required is None:
        required = data.get("required_checks")
        if not required:
            errors.append("task_type requires an explicit nonempty required_checks contract")
    checks = data.get("scientific_checks", {})
    errors.extend(verify_scientific_evidence(root, data))
    for key in required or []:
        check = checks.get(key, {})
        if check.get("status") != "passed" or not check.get("evidence_files"):
            errors.append(f"scientific check lacks passing evidence: {key}")
        if key not in {"heldout_evaluation", "temporal_split", "availability_time", "constraint_residuals", "feasibility"}:
            if check.get("verification_mode") not in {"computed", "model_review", "human_review"}:
                errors.append(f"check must disclose computed or reviewed evidence: {key}")
            elif check["verification_mode"] != "computed" and not all(check.get(k) for k in ("reviewer", "rationale")):
                errors.append(f"review check needs reviewer and rationale: {key}")
    for method in data.get("methods", []):
        degeneracy = method.get("degeneracy_check")
        if method.get("degeneracy_required") is True and not degeneracy:
            errors.append("method requires an output degeneracy check")
        elif degeneracy and degeneracy.get("status") != "passed":
            errors.append("declared output degeneracy check did not pass")
    for path, value in fingerprints(root, referenced_files(data)).items():
        if value is None:
            errors.append(f"missing referenced experiment file: {path}")
    return errors


def execute(root, step, config):
    """Every declared check must have an implementation and an argument binding."""
    outputs = step["outputs"]
    errors = artifact_errors(root, outputs)
    if errors:
        return errors
    sid = step["id"]
    errors.extend(artifact_contract_errors(sid, outputs, root))
    q = step["question_id"]
    summary = root / step.get("run_summary", f"results/{q}/experiments/round1/run_summary.json")
    commands = {
        "artifact_check": ["--workspace", str(root), "--paths", *outputs],
        "method_reference_check": [str(summary), "--method-contract", str(root / f"methods/{q}/method_contract.json")],
        "modeling_coverage_check": [str(summary)],
        "leakage_check": [str(summary)],
        "data_ingest_check": [str(root / "workspace/data/source_registry.json"), "--workspace", str(root)],
        "frozen_number_check": [str(root / f"results/{q}/reports/frozen_numbers.json"), "--workspace", str(root)],
        "claim_code_check": [str(root / f"results/{q}/reports/frozen_numbers.json"), "--workspace", str(root)],
        "reference_check": ["--tex", str(root / "paper"), "--bib", str(root / "paper/refs.bib")],
        "delivery_check": ["--paper-root", str(root / "paper"), "--format", config.get("paper_format", "latex")],
        "docx_delivery_check": ["--paper-root", str(root / "paper")],
    }
    for name in step.get("checks", []):
        if name == "human_decision_check":
            continue  # Runtime checks typed choice and evidence hashes, not just existence.
        if name == "git_context_check":
            context = load(root / outputs[0])
            if not context.get("branch", "").startswith("exp/") or not context.get("parent_commit"):
                errors.append("missing experiment branch and base commit")
            runtime = load(root / "planning/workflow_run.json")
            current = subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True, text=True)
            if context.get("question_id") != q or context.get("experiment_id") != runtime["iterations"].get(q) or current.returncode or current.stdout.strip() != context.get("branch"):
                errors.append("experiment context does not match question, iteration or current branch")
            if context.get("parent_commit") and subprocess.run(["git", "merge-base", "--is-ancestor", context["parent_commit"], "HEAD"], cwd=root, capture_output=True).returncode:
                errors.append("experiment parent commit is not an ancestor of current code")
            continue
        if name == "evidence_check":
            errors.extend(evidence_errors(root, load(root / outputs[0])))
            continue
        if name == "scientific_check":
            errors.extend(scientific_errors(root, load(summary)))
            continue
        if name == "audit_check":
            audit_output = next((raw for raw in reversed(outputs) if raw.endswith(".json")), outputs[-1])
            data = load(root / audit_output)
            if data.get("status") != "passed" or not data.get("evidence_files") or data.get("unresolved") != []:
                errors.append("audit must pass with evidence and no unresolved findings")
            continue
        elif name in commands:
            command = [sys.executable, str(CHECKS / f"{name}.py"), *commands[name]]
        else:
            errors.append(f"unbound validator: {name}")
            continue
        try:
            proc = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            if proc.returncode:
                errors.append(f"{name}: {(proc.stdout or proc.stderr).strip()}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{name}: {exc}")
    return errors
