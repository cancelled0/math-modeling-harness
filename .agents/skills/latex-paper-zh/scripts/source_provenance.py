"""One source-bundle definition shared by PDF/DOCX build and verification."""
from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE_SUFFIXES = {".tex", ".bib", ".cls", ".sty", ".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps"}

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_bundle(root, main):
    records = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES and path != main.with_suffix(".pdf") and not relative.startswith(("exports/", "drafts/")):
            records.append({"path": relative, "sha256": sha256(path)})
    digest = hashlib.sha256()
    for row in records:
        digest.update(row["path"].encode("utf-8") + b"\0" + row["sha256"].encode("ascii") + b"\n")
    return digest.hexdigest(), records
