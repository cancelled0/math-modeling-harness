from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
COMPILE = SKILL_DIR / "scripts" / "compile_latex.py"
DELIVERY = SKILL_DIR / "scripts" / "check_latex_delivery.py"
TEMPLATE = SKILL_DIR / "assets" / "cumcm-template" / "main.tex"


class LatexToolsTest(unittest.TestCase):
    def test_compile_reports_real_capability_and_delivery_never_fakes_pdf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="latex-tool-test-") as temp:
            root = Path(temp)
            main = root / "main.tex"
            shutil.copy2(TEMPLATE, main)
            compile_process = subprocess.run(
                [sys.executable, str(COMPILE), str(main)],
                text=True, encoding="utf-8", errors="replace", capture_output=True,
            )
            report = json.loads((root / "latex_build_report.json").read_text(encoding="utf-8"))
            self.assertIn(report["status"], {"passed", "unavailable"})
            if report["status"] == "passed":
                self.assertEqual(compile_process.returncode, 0)
                self.assertTrue((root / "main.pdf").exists())
            else:
                self.assertEqual(compile_process.returncode, 2)
                self.assertFalse((root / "main.pdf").exists())

            delivery_process = subprocess.run(
                [sys.executable, str(DELIVERY), str(main)],
                text=True, encoding="utf-8", errors="replace", capture_output=True,
            )
            delivery = json.loads((root / "latex_delivery_check.json").read_text(encoding="utf-8"))
            if report["status"] == "unavailable":
                self.assertNotEqual(delivery_process.returncode, 0)
                self.assertEqual(delivery["status"], "failed")


if __name__ == "__main__":
    unittest.main()
