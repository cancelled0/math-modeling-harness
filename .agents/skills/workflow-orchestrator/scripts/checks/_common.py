"""Shared standard-library helpers for harness checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def report(name: str, errors: list[str], warnings: list[str], checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "check": name,
        "status": "PASSED" if not errors else "FAILED",
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }


def emit(value: dict[str, Any], output: Path | None = None) -> int:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if value.get("status") == "PASSED" else 1


def resolve_inside(workspace: Path, raw: str) -> Path:
    path = Path(raw)
    candidate = path.resolve() if path.is_absolute() else (workspace / path).resolve()
    candidate.relative_to(workspace.resolve())
    return candidate


def json_locator(value: Any, locator: str) -> Any:
    if not locator.startswith("$."):
        raise ValueError(f"unsupported JSON locator: {locator}")
    current = value
    for token in locator[2:].split("."):
        if not isinstance(current, dict) or token not in current:
            raise KeyError(locator)
        current = current[token]
    return current
