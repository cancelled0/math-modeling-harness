#!/usr/bin/env python3
"""Safe Git helpers for versioned mathematical-modeling experiments."""

from __future__ import annotations

import argparse
import json
import hashlib
import os
import platform
import time
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTECTED_PATTERNS = (
    re.compile(r"(^|/)(\.env($|\.)|.*credentials.*\.json$|.*secrets.*\.json$)", re.I),
    re.compile(r"\.(pem|key)$", re.I),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=check,
    )


def ensure_repo(root: Path) -> None:
    result = run_git(root, "rev-parse", "--is-inside-work-tree", check=False)
    if result.returncode or result.stdout.strip() != "true":
        raise RuntimeError(f"not a Git repository: {root}")


def branch(root: Path) -> str:
    return run_git(root, "branch", "--show-current").stdout.strip()


def head(root: Path) -> str:
    return run_git(root, "rev-parse", "HEAD").stdout.strip()


def require_clean(root: Path) -> None:
    # Unrelated untracked files do not belong to an experiment. Git itself rejects
    # a switch that would overwrite one; never add them to make the tree clean.
    dirty = run_git(root, "status", "--porcelain", "--untracked-files=no").stdout.strip()
    if dirty:
        raise RuntimeError("working tree is not clean; classify or commit the existing changes first")


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = re.sub(r"[^\w.-]+", "-", value, flags=re.UNICODE).strip("-.")
    if not value:
        raise ValueError("branch component becomes empty after normalization")
    return value


def relative_path(root: Path, raw: str) -> str:
    candidate = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    try:
        rel = candidate.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path is outside workspace: {raw}") from exc
    if any(pattern.search(rel) for pattern in PROTECTED_PATTERNS):
        raise ValueError(f"refusing to stage protected path: {rel}")
    return rel


def require_experiment_branch(name: str, base: str) -> None:
    if name == base or not name.startswith("exp/"):
        raise ValueError(f"expected an exp/ branch distinct from base {base}: {name}")


def append_registry(root: Path, record: dict[str, Any]) -> Path:
    path = root / "planning" / "experiment_registry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def commit_paths(root: Path, paths: list[str], message: str) -> str:
    if not paths:
        raise ValueError("at least one explicit path is required")
    existing_staged = run_git(root, "diff", "--cached", "--name-only", "-z").stdout.strip("\0")
    if existing_staged:
        raise RuntimeError("index already contains staged changes; refusing to include unrelated work")
    rels = list(dict.fromkeys(relative_path(root, item) for item in paths))
    for rel in rels:
        candidate = root / rel
        if {"data_raw", ".venv", "venv", "__pycache__", "node_modules"}.intersection(Path(rel).parts):
            raise ValueError(f"raw data/cache/environment must not be committed: {rel}")
        if candidate.is_file() and candidate.stat().st_size > 20 * 1024 * 1024:
            raise ValueError(f"large artifact requires path/hash registration: {rel}")
        tracked = run_git(root, "ls-files", "--error-unmatch", "--", rel, check=False).returncode == 0
        if not candidate.is_file() and not tracked:
            raise ValueError(f"explicit commit path is neither a file nor a tracked deletion: {rel}")
    run_git(root, "add", "--", *rels)
    staged = [item for item in run_git(root, "diff", "--cached", "--name-only", "-z").stdout.split("\0") if item]
    if not staged:
        raise RuntimeError("no staged changes for the requested paths")
    unexpected = sorted(set(staged) - set(rels))
    if unexpected:
        run_git(root, "restore", "--staged", "--", *staged, check=False)
        raise RuntimeError("staging expanded beyond explicit files: " + ", ".join(unexpected))
    run_git(root, "commit", "-m", message)
    return head(root)


def cmd_status(root: Path, _: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    return {
        "status": "OK",
        "branch": branch(root),
        "commit": head(root),
        "working_tree": run_git(root, "status", "--porcelain").stdout.splitlines(),
    }


def cmd_checkpoint(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    commit = commit_paths(root, args.paths, args.message)
    return {"status": "COMMITTED", "commit": commit, "branch": branch(root)}


def cmd_start(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    runtime = root / "planning/workflow_run.json"
    experiment_id = getattr(args, "experiment_id", None)
    if runtime.is_file():
        active_id = json.loads(runtime.read_text(encoding="utf-8"))["iterations"][args.question.upper()]
        if experiment_id and experiment_id != active_id:
            raise ValueError("experiment ID differs from workflow iteration")
        experiment_id = active_id
    name = f"exp/{slug(args.contest)}/{slug(args.question)}/{slug(args.algorithm)}"
    if run_git(root, "show-ref", "--verify", f"refs/heads/{name}", check=False).returncode == 0:
        raise RuntimeError(f"experiment branch already exists: {name}")
    target = getattr(args, "worktree", None)
    if target:
        target = Path(target).resolve()
        if target.exists():
            raise ValueError("worktree destination already exists")
        run_git(root, "worktree", "add", "-b", name, str(target), args.base)
        root = target
    else:
        require_clean(root)
        if not getattr(args, "from_current", False):
            run_git(root, "switch", args.base)
        run_git(root, "switch", "-c", name)
    context = {
        "schema_version": 1,
        "status": "active",
        "contest": args.contest,
        "question_id": args.question.upper(),
        "experiment_id": experiment_id,
        "algorithm": args.algorithm,
        "branch": name,
        "base_branch": args.base,
        "parent_commit": head(root),
        "started_at": now(),
        "workspace": str(root),
    }
    context_path = root / "planning" / "experiments" / args.question.upper() / "active_experiment.json"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "STARTED", **context, "context": context_path.relative_to(root).as_posix()}


def validate_active_context(root, args):
    summary_relative = relative_path(root, args.summary)
    runtime_path = root / "planning/workflow_run.json"
    if runtime_path.is_file():
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        matches = [q for q, eid in runtime["iterations"].items()
                   if eid == args.experiment_id and summary_relative == f"results/{q}/experiments/{eid}/run_summary.json"]
        if len(matches) != 1:
            raise ValueError("summary directory and experiment ID must match the active workflow")
        context = json.loads((root / f"planning/experiments/{matches[0]}/active_experiment.json").read_text(encoding="utf-8"))
        if context.get("experiment_id") != args.experiment_id or context.get("branch") != branch(root):
            raise ValueError("prepare the current experiment branch/context before execution")
        run_git(root, "merge-base", "--is-ancestor", context["parent_commit"], "HEAD")


def cmd_record(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    validate_active_context(root, args)
    summary_relative = relative_path(root, args.summary)
    summary_path = root / summary_relative
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    execution = summary.get("execution", {})
    receipt_path = root / relative_path(root, execution.get("receipt_file", ""))
    if not receipt_path.is_file():
        raise ValueError("run through the run command before record; missing execution receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    code_commit = execution.get("code_commit")
    if not code_commit or receipt.get("code_commit") != code_commit or receipt.get("exit_code") != 0 or receipt.get("status") != "success":
        raise ValueError("invalid execution receipt")
    if summary.get("experiment_id") != args.experiment_id or receipt.get("experiment_id") != args.experiment_id:
        raise ValueError("experiment ID mismatch")
    for raw, expected in receipt.get("files", {}).items():
        path = root / relative_path(root, raw)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"executed input/output changed: {raw}")
    run_git(root, "merge-base", "--is-ancestor", code_commit, "HEAD")
    registry = append_registry(root, {
        "schema_version": 1,
        "event": "experiment_recorded",
        "experiment_id": args.experiment_id,
        "question_id": summary.get("question_id") or summary.get("question"),
        "branch": branch(root),
        "code_commit": code_commit,
        "summary": summary_path.relative_to(root).as_posix(),
        "recorded_at": now(),
    })
    question_id = str(summary.get("question_id") or summary.get("question") or "").upper()
    context_path = root / "planning" / "experiments" / question_id / "active_experiment.json"
    evidence_paths = [summary_relative, receipt_path.relative_to(root).as_posix(), registry.relative_to(root).as_posix()]
    evidence_paths.extend(receipt.get("output_files", []))
    evidence_paths.extend(relative_path(root, p) for p in (args.paths or []))
    if context_path.exists():
        evidence_paths.append(context_path.relative_to(root).as_posix())
    evidence_commit = commit_paths(
        root,
        evidence_paths,
        f"evidence: record {args.experiment_id}",
    )
    return {
        "status": "RECORDED",
        "experiment_id": args.experiment_id,
        "code_commit": code_commit,
        "evidence_commit": evidence_commit,
        "branch": branch(root),
    }


def cmd_run(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    receipt = root / relative_path(root, args.summary)
    receipt = receipt.with_name("execution_receipt.json")
    if receipt.exists():
        raise ValueError("attempt already recorded; preserve it and use a fresh experiment ID/directory")
    try:
        return execute_run(root, args)
    except (Exception, KeyboardInterrupt) as exc:
        if receipt.exists():
            data = json.loads(receipt.read_text(encoding="utf-8"))
            data.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                        failure_reason=str(exc) or type(exc).__name__, finished_at=now())
            if isinstance(exc, subprocess.TimeoutExpired):
                data["status"] = "timeout"
            receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"execution unsuccessful: {exc}; receipt: {receipt}") from exc


def execute_run(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Execute already committed code, capture actual environment and file hashes."""
    ensure_repo(root)
    validate_active_context(root, args)
    command = list(args.argv)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise ValueError("missing executable argv after --")
    code_commit = head(root)
    code_files = [relative_path(root, p) for p in args.code_paths]
    for raw in code_files:
        run_git(root, "ls-files", "--error-unmatch", "--", raw)
        if run_git(root, "diff", "HEAD", "--", raw).stdout:
            raise ValueError(f"commit code before execution: {raw}")
    input_files = [relative_path(root, p) for p in args.inputs]
    before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in code_files + input_files}
    summary_relative = relative_path(root, args.summary)
    summary_path = root / summary_relative
    if summary_path.exists():
        raise ValueError("run summary already exists; use a fresh experiment ID/directory")
    started = now()
    begin = time.monotonic()
    receipt_path = summary_path.with_name("execution_receipt.json")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    log = summary_path.with_name("execution.log")
    receipt = {"schema_version": 1, "code_commit": code_commit, "experiment_id": args.experiment_id,
               "argv": command, "started_at": started, "status": "running", "exit_code": None,
               "files": before, "log": log.relative_to(root).as_posix()}
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.Popen(command, cwd=root, stdout=handle, stderr=subprocess.STDOUT,
                                start_new_session=os.name != "nt")
        try:
            proc.wait(timeout=args.timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
            else:
                import signal
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise
    elapsed = time.monotonic() - begin
    receipt.update(exit_code=proc.returncode, finished_at=now(), status="validating")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if proc.returncode or not summary_path.is_file():
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        raise RuntimeError(f"execution failed or no run summary; see {log}")
    for raw, expected in before.items():
        if hashlib.sha256((root / raw).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"input/code changed during execution: {raw}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["experiment_id"] = args.experiment_id
    summary["execution"] = {"code_commit": code_commit, "receipt_file": receipt_path.relative_to(root).as_posix()}
    summary["environment"] = {**summary.get("environment", {}), "runner_python": sys.version, "platform": platform.platform(), "argv": command,
                              "runner_packages": subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.splitlines()}
    summary["runtime_seconds"] = elapsed
    # The model program must record the seed it actually used, not an assumed CLI seed.
    if "random_seed" not in summary:
        raise ValueError("model program must report its actual random_seed")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    output_files = [p for method in summary.get("methods", []) for p in method.get("output_files", [])]
    for raw in [summary_relative, *output_files]:
        rel = relative_path(root, raw)
        receipt["files"][rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    receipt["output_files"] = [summary_relative, *output_files, log.relative_to(root).as_posix()]
    receipt["status"] = "success"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "EXECUTED", "code_commit": code_commit, "receipt": str(receipt_path), "summary": summary_relative}


def verify_decision(root, args, choice):
    paths = [root / args.decision_file] if getattr(args, "decision_file", None) else list((root / "methods").rglob("*_decisions.jsonl"))
    found = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("decision_id") == args.decision_id:
                    found.append((path, row))
    if len(found) != 1:
        raise ValueError("decision ID must resolve to exactly one real ledger record")
    path, row = found[0]
    if row.get("decided_by") != "human" or row.get("status") != "DECIDED" or row.get("choice") != choice or not row.get("user_message"):
        raise ValueError("decision does not authorize this Git action")
    hashes = row.get("evidence_hashes", {})
    summaries = [p for p in hashes if p.endswith("run_summary.json")]
    if not summaries or not row.get("experiment_id"):
        raise ValueError("decision must bind an experiment and run summary")
    for raw, expected in hashes.items():
        if raw.endswith("/"):
            continue
        file = root / relative_path(root, raw)
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError(f"decision evidence is stale: {raw}")
    for raw in summaries:
        summary = json.loads((root / raw).read_text(encoding="utf-8"))
        if summary.get("experiment_id") != row["experiment_id"]:
            raise ValueError("decision experiment mismatch")
        commit = summary.get("execution", {}).get("code_commit")
        if not commit or run_git(root, "merge-base", "--is-ancestor", commit, args.branch, check=False).returncode:
            raise ValueError("experiment code is not on the target branch")
    return path


def checkpoint_generated_state(root, decision_file):
    """Persist only named harness control records before a branch transition."""
    names = ["planning/workflow_run.json", "planning/artifacts.json", "planning/events.jsonl", "planning/experiment_registry.jsonl"]
    names.extend(p.relative_to(root).as_posix() for p in (root / "planning/manifests").glob("*.json"))
    names.append(decision_file.relative_to(root).as_posix())
    changed = []
    for raw in names:
        if (root / raw).is_file() and run_git(root, "status", "--porcelain", "--", raw).stdout.strip():
            changed.append(raw)
    if changed:
        commit_paths(root, changed, "checkpoint: workflow evidence and human decision")


def cmd_accept(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    require_experiment_branch(args.branch, args.base)
    decision_file = verify_decision(root, args, "accept")
    checkpoint_generated_state(root, decision_file)
    require_clean(root)
    run_git(root, "show-ref", "--verify", f"refs/heads/{args.branch}")
    run_git(root, "switch", args.base)
    run_git(root, "merge", "--no-ff", args.branch, "-m", f"accept: {args.branch} ({args.decision_id})")
    registry = append_registry(root, {
        "schema_version": 1,
        "event": "experiment_accepted",
        "branch": args.branch,
        "decision_id": args.decision_id,
        "merge_commit": head(root),
        "recorded_at": now(),
    })
    record_commit = commit_paths(root, [registry.relative_to(root).as_posix()], f"accept: record {args.decision_id}")
    return {"status": "ACCEPTED", "branch": args.branch, "base": args.base, "commit": record_commit}


def cmd_reject(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    require_experiment_branch(args.branch, args.base)
    decision_file = verify_decision(root, args, "reject")
    checkpoint_generated_state(root, decision_file)
    require_clean(root)
    run_git(root, "switch", args.branch)
    registry = append_registry(root, {
        "schema_version": 1,
        "event": "experiment_rejected",
        "branch": args.branch,
        "decision_id": args.decision_id,
        "commit": head(root),
        "recorded_at": now(),
    })
    record_commit = commit_paths(root, [registry.relative_to(root).as_posix()], f"exp: record rejection {args.decision_id}")
    run_git(root, "switch", args.base)
    stable_registry = append_registry(root, {
        "schema_version": 1,
        "event": "experiment_rejected",
        "branch": args.branch,
        "decision_id": args.decision_id,
        "preserved_commit": record_commit,
        "recorded_at": now(),
    })
    stable_commit = commit_paths(root, [stable_registry.relative_to(root).as_posix()], f"revert: retain rejection {args.decision_id}")
    return {
        "status": "REJECTED",
        "branch": args.branch,
        "preserved_commit": record_commit,
        "returned_to": args.base,
        "stable_record_commit": stable_commit,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--question", required=True)
    checkpoint.add_argument("--message", required=True)
    checkpoint.add_argument("--paths", nargs="+", required=True)

    start = sub.add_parser("start")
    start.add_argument("--contest", required=True)
    start.add_argument("--question", required=True)
    start.add_argument("--algorithm", required=True)
    start.add_argument("--base", default="main")
    start.add_argument("--experiment-id")
    start.add_argument("--from-current", action="store_true", help="branch from a committed current checkpoint, preserving workflow and rejected evidence")
    start.add_argument("--worktree", type=Path, help="optional isolated checkout; existing checkout stays in place")

    execute = sub.add_parser("run")
    execute.add_argument("--experiment-id", required=True)
    execute.add_argument("--summary", required=True)
    execute.add_argument("--code-paths", nargs="+", required=True)
    execute.add_argument("--inputs", nargs="*", default=[])
    execute.add_argument("--timeout", type=int, default=600)
    execute.add_argument("argv", nargs=argparse.REMAINDER)

    record = sub.add_parser("record")
    record.add_argument("--experiment-id", required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--message", required=True)
    record.add_argument("--paths", nargs="*", default=[], help="additional explicit evidence files; code must already be committed")

    for name in ("accept", "reject"):
        action = sub.add_parser(name)
        action.add_argument("--branch", required=True)
        action.add_argument("--decision-id", required=True)
        action.add_argument("--base", default="main")
        action.add_argument("--decision-file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.workspace.resolve()
    handlers = {
        "status": cmd_status,
        "checkpoint": cmd_checkpoint,
        "start": cmd_start,
        "record": cmd_record,
        "run": cmd_run,
        "accept": cmd_accept,
        "reject": cmd_reject,
    }
    try:
        result = handlers[args.command](root, args)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        print(json.dumps({"status": "FAILED", "error": detail}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
