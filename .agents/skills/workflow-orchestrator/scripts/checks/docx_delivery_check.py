#!/usr/bin/env python3
"""Verify that the LaTeX-derived DOCX mirror is current and structurally accepted."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

from _common import emit, load_object, report, sha256


SOURCE_SUFFIXES = {".tex", ".bib", ".cls", ".sty", ".png", ".jpg", ".jpeg", ".pdf", ".svg"}


def source_bundle(root: Path, main: Path) -> str:
    records: list[tuple[str, str]] = []
    generated_pdf = main.with_suffix(".pdf")
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES or path == generated_pdf:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith("exports/"):
            continue
        records.append((relative, sha256(path)))
    digest = hashlib.sha256()
    for relative, file_hash in records:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", type=Path, default=Path("paper"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.paper_root.resolve()
    source = root / "main.tex"
    docx = root / "exports" / "main.docx"
    export_report_path = root / "docx_export_report.json"
    delivery_report_path = root / "docx_delivery_check.json"
    errors: list[str] = []
    warnings: list[str] = []
    checks = {
        "canonical_source": str(source),
        "derived_docx": str(docx),
        "docx_is_derived": True,
    }
    for path in (source, docx, export_report_path, delivery_report_path):
        exists = path.is_file() and path.stat().st_size > 0
        checks[f"exists:{path.name}"] = exists
        if not exists:
            errors.append(f"missing delivery artifact: {path}")
    if docx.is_file() and not zipfile.is_zipfile(docx):
        errors.append("derived DOCX is not a valid ZIP package")
    if not errors:
        try:
            export_report = load_object(export_report_path)
            delivery_report = load_object(delivery_report_path)
        except (OSError, ValueError) as exc:
            errors.append(f"invalid DOCX report: {exc}")
        else:
            if export_report.get("status") != "passed":
                errors.append(f"DOCX export status is {export_report.get('status')}")
            if delivery_report.get("status") not in {"passed", "passed_with_visual_check_pending"}:
                errors.append(f"DOCX delivery status is {delivery_report.get('status')}")
            if export_report.get("source_sha256") != sha256(source):
                errors.append("DOCX mirror is stale relative to canonical LaTeX")
            if export_report.get("source_bundle_sha256") != source_bundle(root, source):
                errors.append("DOCX mirror is stale relative to the LaTeX source bundle")
            for dependency_name in ("reference_doc", "bibliography"):
                dependency = export_report.get(dependency_name)
                if not dependency:
                    continue
                dependency_path = Path(str(dependency.get("path", "")))
                if not dependency_path.is_file():
                    errors.append(f"recorded {dependency_name} is missing")
                elif dependency.get("sha256") != sha256(dependency_path):
                    errors.append(f"DOCX mirror is stale relative to {dependency_name}")
            if export_report.get("output_sha256") != sha256(docx):
                errors.append("DOCX differs from the recorded derived artifact")
            if delivery_report.get("status") == "passed_with_visual_check_pending":
                warnings.append("DOCX structural checks passed; visual page inspection remains required")
    return emit(report("docx_delivery_check", errors, warnings, checks), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
