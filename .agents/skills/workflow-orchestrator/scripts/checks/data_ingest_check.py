#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from _common import emit, load_object, report, resolve_inside, sha256


REQUIRED = {"source_id", "kind", "publisher", "title", "url", "status"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    data = load_object(args.registry)
    sources = data.get("sources", data.get("items", []))
    if not isinstance(sources, list):
        errors.append("registry sources/items must be a list")
        sources = []
    checked = []
    for index, source in enumerate(sources):
        missing = sorted(REQUIRED - set(source)) if isinstance(source, dict) else sorted(REQUIRED)
        if missing:
            errors.append(f"source[{index}] missing fields: {', '.join(missing)}")
            continue
        status = source.get("status")
        local = source.get("local_path")
        expected = source.get("sha256")
        row = {"source_id": source.get("source_id"), "status": status, "hash_match": None}
        if status in {"retrieved", "verified"}:
            if not local or not expected:
                errors.append(f"{source.get('source_id')}: retrieved source requires local_path and sha256")
            else:
                try:
                    path = resolve_inside(args.workspace.resolve(), local)
                except ValueError:
                    errors.append(f"{source.get('source_id')}: local_path outside workspace")
                else:
                    if not path.exists():
                        errors.append(f"{source.get('source_id')}: local file missing")
                    else:
                        row["hash_match"] = sha256(path) == expected
                        if not row["hash_match"]:
                            errors.append(f"{source.get('source_id')}: sha256 mismatch")
        elif status == "planned" and expected:
            errors.append(f"{source.get('source_id')}: planned source must not invent a hash")
        checked.append(row)
    if not sources:
        warnings.append("registry contains no external sources; acceptable only when the data inventory explicitly needs none")
    return emit(report("data_ingest_check", errors, warnings, {"sources": checked}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
