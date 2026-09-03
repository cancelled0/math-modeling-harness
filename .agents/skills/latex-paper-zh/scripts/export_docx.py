#!/usr/bin/env python3
"""Export a derived DOCX mirror from the canonical LaTeX paper."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_DOCX_MEMBERS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
    "word/styles.xml",
}
SOURCE_SUFFIXES = {".tex", ".bib", ".cls", ".sty", ".png", ".jpg", ".jpeg", ".pdf", ".svg"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate_pandoc() -> str | None:
    custom = os.environ.get("MODELING_PANDOC")
    if custom:
        candidate = Path(custom)
        if candidate.is_dir():
            candidate = candidate / ("pandoc.exe" if os.name == "nt" else "pandoc")
        if candidate.is_file():
            return str(candidate)
    return shutil.which("pandoc")


def pandoc_version(command: str) -> str | None:
    try:
        process = subprocess.run(
            [command, "--version"], text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return process.stdout.splitlines()[0].strip() if process.returncode == 0 and process.stdout else None


def docx_valid(path: Path) -> tuple[bool, list[str]]:
    if not path.exists() or path.stat().st_size == 0:
        return False, ["Pandoc did not create a non-empty DOCX"]
    if not zipfile.is_zipfile(path):
        return False, ["Pandoc output is not a valid DOCX ZIP container"]
    with zipfile.ZipFile(path) as archive:
        missing = sorted(REQUIRED_DOCX_MEMBERS - set(archive.namelist()))
    return not missing, [f"DOCX is missing package member: {item}" for item in missing]


def file_record(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return {"path": str(path), "sha256": sha256(path)}


def source_bundle(root: Path, main: Path) -> tuple[str, list[dict[str, str]]]:
    records: list[dict[str, str]] = []
    generated_pdf = main.with_suffix(".pdf")
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES or path == generated_pdf:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("exports/"):
            continue
        records.append({"path": relative, "sha256": sha256(path)})
    digest = hashlib.sha256()
    for item in records:
        digest.update(item["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(item["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), records


def export(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    source = args.main_tex.resolve()
    output = (args.output or source.parent / "exports" / "main.docx").resolve()
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "failed",
        "canonical_source": str(source),
        "canonical_format": "latex",
        "docx_is_derived": True,
        "reverse_sync_allowed": False,
        "source_sha256": None,
        "source_bundle_sha256": None,
        "source_files": [],
        "output": str(output),
        "output_sha256": None,
        "pandoc": None,
        "pandoc_version": None,
        "reference_doc": None,
        "bibliography": None,
        "resource_paths": [],
        "command": None,
        "started_at": now(),
        "warnings": [],
        "errors": [],
    }
    if not source.is_file():
        report["errors"].append("canonical LaTeX source does not exist")
        return report, 1
    report["source_sha256"] = sha256(source)
    report["source_bundle_sha256"], report["source_files"] = source_bundle(source.parent, source)

    pandoc = locate_pandoc()
    if not pandoc:
        report["status"] = "unavailable"
        report["errors"].append("Pandoc is unavailable; install it or set MODELING_PANDOC")
        return report, 2
    report["pandoc"] = pandoc
    report["pandoc_version"] = pandoc_version(pandoc)

    reference_doc = args.reference_doc.resolve() if args.reference_doc else None
    if reference_doc and not reference_doc.is_file():
        report["errors"].append(f"reference DOCX does not exist: {reference_doc}")
        return report, 1
    report["reference_doc"] = file_record(reference_doc)

    bibliography = args.bibliography.resolve() if args.bibliography else None
    if bibliography is None:
        bibliography = next(
            (candidate for candidate in (source.parent / "refs.bib", source.parent / "references.bib") if candidate.is_file()),
            None,
        )
    if bibliography and not bibliography.is_file():
        report["errors"].append(f"bibliography does not exist: {bibliography}")
        return report, 1
    report["bibliography"] = file_record(bibliography)

    resource_paths = [path.resolve() for path in (args.resource_path or [source.parent])]
    missing_resources = [str(path) for path in resource_paths if not path.exists()]
    if missing_resources:
        report["errors"].append("resource path does not exist: " + ", ".join(missing_resources))
        return report, 1
    report["resource_paths"] = [str(path) for path in resource_paths]

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".docx-export-", suffix=".docx", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    command = [
        pandoc,
        str(source),
        "--from=latex",
        "--to=docx",
        "--standalone",
        f"--resource-path={os.pathsep.join(str(path) for path in resource_paths)}",
        "--output",
        str(temporary),
    ]
    if reference_doc:
        command.extend(["--reference-doc", str(reference_doc)])
    if bibliography:
        command.extend(["--citeproc", "--bibliography", str(bibliography)])
    report["command"] = command
    try:
        process = subprocess.run(
            command,
            cwd=source.parent,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=args.timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if temporary.exists():
            temporary.unlink()
        report["errors"].append(str(exc))
        return report, 1

    report["returncode"] = process.returncode
    report["stdout_tail"] = "\n".join(process.stdout.splitlines()[-80:])
    report["stderr_tail"] = "\n".join(process.stderr.splitlines()[-80:])
    if process.returncode:
        if temporary.exists():
            temporary.unlink()
        report["errors"].append(f"Pandoc returned {process.returncode}")
        return report, 1

    valid, errors = docx_valid(temporary)
    if not valid:
        if temporary.exists():
            temporary.unlink()
        report["errors"].extend(errors)
        return report, 1

    os.replace(temporary, output)
    report["output_sha256"] = sha256(output)
    report["status"] = "passed"
    report["completed_at"] = now()
    report["warnings"].append("DOCX is a review/submission mirror; edit canonical LaTeX and regenerate it")
    return report, 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("main_tex", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--reference-doc", type=Path)
    parser.add_argument("--bibliography", type=Path)
    parser.add_argument("--resource-path", action="append", type=Path)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    result, code = export(args)
    report_path = (args.report or args.main_tex.resolve().parent / "docx_export_report.json").resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
