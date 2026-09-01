#!/usr/bin/env python3
"""Safe Git helpers for versioned mathematical-modeling experiments."""

from __future__ import annotations

import argparse
import json
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
    dirty = run_git(root, "status", "--porcelain").stdout.strip()
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
    require_clean(root)
    run_git(root, "switch", args.base)
    name = f"exp/{slug(args.contest)}/{slug(args.question)}/{slug(args.algorithm)}"
    if run_git(root, "show-ref", "--verify", f"refs/heads/{name}", check=False).returncode == 0:
        raise RuntimeError(f"experiment branch already exists: {name}")
    run_git(root, "switch", "-c", name)
    context = {
        "schema_version": 1,
        "status": "active",
        "contest": args.contest,
        "question_id": args.question.upper(),
        "algorithm": args.algorithm,
        "branch": name,
        "base_branch": args.base,
        "parent_commit": head(root),
        "started_at": now(),
    }
    context_path = root / "planning" / "experiments" / args.question.upper() / "active_experiment.json"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "STARTED", **context, "context": context_path.relative_to(root).as_posix()}


def cmd_record(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    summary_relative = relative_path(root, args.summary)
    summary_path = root / summary_relative
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    parent = head(root)
    code_commit = commit_paths(root, args.paths, args.message)
    summary["experiment_id"] = args.experiment_id
    summary["git"] = {
        "branch": branch(root),
        "parent_commit": parent,
        "code_commit": code_commit,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
    evidence_paths = [summary_path.relative_to(root).as_posix(), registry.relative_to(root).as_posix()]
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


def cmd_accept(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_repo(root)
    require_clean(root)
    require_experiment_branch(args.branch, args.base)
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
    require_clean(root)
    require_experiment_branch(args.branch, args.base)
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

    record = sub.add_parser("record")
    record.add_argument("--experiment-id", required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--message", required=True)
    record.add_argument("--paths", nargs="+", required=True)

    for name in ("accept", "reject"):
        action = sub.add_parser(name)
        action.add_argument("--branch", required=True)
        action.add_argument("--decision-id", required=True)
        action.add_argument("--base", default="main")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.workspace.resolve()
    handlers = {
        "status": cmd_status,
        "checkpoint": cmd_checkpoint,
        "start": cmd_start,
        "record": cmd_record,
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
