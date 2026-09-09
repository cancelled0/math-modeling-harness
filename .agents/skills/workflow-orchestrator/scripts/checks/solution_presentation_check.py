#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _common import emit, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    script = Path(__file__).resolve().parents[3] / "modeling-results-presenter" / "scripts" / "present_results.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--workspace", str(args.workspace), "--spec", str(args.spec), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
    )
    errors = [] if proc.returncode == 0 else [(proc.stdout or proc.stderr).strip()]
    return emit(report("solution_presentation_check", errors, [], {"spec": str(args.spec)}), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
