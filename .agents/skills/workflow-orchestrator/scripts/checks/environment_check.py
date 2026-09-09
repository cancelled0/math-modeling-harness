#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from _common import emit, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--language", choices=("auto", "python", "matlab"), default="auto")
    parser.add_argument("--packages", nargs="*", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    capabilities = {
        "python": sys.executable,
        "git": shutil.which("git"),
        "matlab": shutil.which("matlab"),
        "packages": {name: importlib.util.find_spec(name) is not None for name in args.packages},
    }
    if not capabilities["git"]:
        errors.append("git is unavailable")
    else:
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=args.workspace,
            capture_output=True,
            text=True,
        )
        capabilities["git_repository"] = probe.returncode == 0 and probe.stdout.strip() == "true"
        if not capabilities["git_repository"]:
            errors.append("workspace is not inside a Git repository")
    if args.language == "matlab" and not capabilities["matlab"]:
        errors.append("MATLAB runtime is unavailable")
    missing_packages = [name for name, present in capabilities["packages"].items() if not present]
    if missing_packages:
        errors.append("missing Python packages: " + ", ".join(missing_packages))
    if args.language == "auto" and not capabilities["matlab"]:
        warnings.append("MATLAB unavailable; automatic implementation will use Python")
    return emit(report("environment_check", errors, warnings, capabilities), args.output)


if __name__ == "__main__":
    raise SystemExit(main())
