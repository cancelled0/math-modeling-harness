#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _common import emit, report, resolve_inside


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--paths", nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    checks = {}
    for raw in args.paths:
        try:
            path = resolve_inside(args.workspace.resolve(), raw)
        except ValueError:
            errors.append(f"outside workspace: {raw}")
            continue
        valid = path.exists() and path.is_file() and path.stat().st_size > 0
        if valid and path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                valid = False
        if valid and path.suffix == ".jsonl":
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        json.loads(line)
            except (OSError, json.JSONDecodeError):
                valid = False
        checks[raw] = valid
        if not valid:
            errors.append(f"missing, empty, or invalid artifact: {raw}")
    return emit(report("artifact_check", errors, [], checks), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
