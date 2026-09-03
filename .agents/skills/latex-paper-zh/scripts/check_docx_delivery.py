#!/usr/bin/env python3
"""Structurally validate a derived DOCX and detect a stale LaTeX mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


REQUIRED_MEMBERS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
    "word/styles.xml",
}
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
SOURCE_SUFFIXES = {".tex", ".bib", ".cls", ".sty", ".png", ".jpg", ".jpeg", ".pdf", ".svg"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


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


def check(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    docx = args.docx.resolve()
    source = args.source_tex.resolve() if args.source_tex else None
    export_report_path = args.export_report.resolve() if args.export_report else None
    visual_report_path = args.visual_report.resolve() if args.visual_report else None
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "failed",
        "docx": str(docx),
        "canonical_source": str(source) if source else None,
        "canonical_format": "latex",
        "docx_is_derived": True,
        "reverse_sync_allowed": False,
        "visual_render_check_required": True,
        "checks": {},
        "warnings": [],
        "errors": [],
    }
    if not docx.is_file() or docx.stat().st_size == 0:
        result["errors"].append("derived DOCX is missing or empty")
        return result, 1
    if not zipfile.is_zipfile(docx):
        result["errors"].append("derived DOCX is not a valid ZIP package")
        return result, 1

    with zipfile.ZipFile(docx) as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED_MEMBERS - names)
        result["checks"]["required_package_members"] = not missing
        result["errors"].extend(f"missing DOCX package member: {item}" for item in missing)
        if "word/document.xml" in names:
            try:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
            except ElementTree.ParseError as exc:
                result["errors"].append(f"word/document.xml is invalid: {exc}")
            else:
                texts = [node.text or "" for node in root.findall(f".//{{{W_NS}}}t")]
                result["checks"].update({
                    "non_whitespace_characters": len("".join(texts).strip()),
                    "paragraphs": len(root.findall(f".//{{{W_NS}}}p")),
                    "tables": len(root.findall(f".//{{{W_NS}}}tbl")),
                    "images": len([name for name in names if name.startswith("word/media/")]),
                    "equations": len(root.findall(f".//{{{M_NS}}}oMath")),
                })
                if result["checks"]["non_whitespace_characters"] == 0:
                    result["errors"].append("derived DOCX has no visible text")

    current_docx_hash = sha256(docx)
    result["checks"]["docx_sha256"] = current_docx_hash
    if source:
        if not source.is_file():
            result["errors"].append("canonical LaTeX source is missing")
        else:
            result["checks"]["source_sha256"] = sha256(source)
            result["checks"]["source_bundle_sha256"] = source_bundle(source.parent, source)
    if export_report_path:
        if not export_report_path.is_file():
            result["errors"].append("DOCX export report is missing")
        else:
            try:
                export_report = load_object(export_report_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                result["errors"].append(f"invalid DOCX export report: {exc}")
            else:
                result["checks"]["export_status"] = export_report.get("status")
                if export_report.get("status") != "passed":
                    result["errors"].append(f"DOCX export status is {export_report.get('status')}")
                if export_report.get("output_sha256") != current_docx_hash:
                    result["errors"].append("DOCX hash no longer matches its export report")
                if source and source.is_file() and export_report.get("source_sha256") != sha256(source):
                    result["errors"].append("DOCX mirror is stale relative to canonical LaTeX")
                if source and source.is_file() and export_report.get("source_bundle_sha256") != source_bundle(source.parent, source):
                    result["errors"].append("DOCX mirror is stale relative to the LaTeX source bundle")
                for dependency_name in ("reference_doc", "bibliography"):
                    dependency = export_report.get(dependency_name)
                    if not dependency:
                        continue
                    dependency_path = Path(str(dependency.get("path", "")))
                    if not dependency_path.is_file():
                        result["errors"].append(f"recorded {dependency_name} is missing")
                    elif dependency.get("sha256") != sha256(dependency_path):
                        result["errors"].append(f"DOCX mirror is stale relative to {dependency_name}")

    if visual_report_path:
        if not visual_report_path.is_file():
            result["errors"].append("requested visual render report is missing")
        else:
            try:
                visual = load_object(visual_report_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                result["errors"].append(f"invalid visual render report: {exc}")
            else:
                visual_ok = str(visual.get("status", "")).lower() in {"passed", "pass"} and not visual.get("errors")
                result["checks"]["visual_render_passed"] = visual_ok
                if not visual_ok:
                    result["errors"].append("DOCX visual render check did not pass")

    if not result["errors"]:
        if visual_report_path:
            result["status"] = "passed"
            result["visual_render_check_required"] = False
        else:
            result["status"] = "passed_with_visual_check_pending"
            result["warnings"].append("render the DOCX and inspect all pages before final delivery")
    return result, 0 if not result["errors"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--source-tex", type=Path)
    parser.add_argument("--export-report", type=Path)
    parser.add_argument("--visual-report", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result, code = check(args)
    report_path = (args.report or args.docx.resolve().parent / "docx_delivery_check.json").resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
