from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
COMPILE = SKILL_DIR / "scripts" / "compile_latex.py"
DELIVERY = SKILL_DIR / "scripts" / "check_latex_delivery.py"
EXPORT_DOCX = SKILL_DIR / "scripts" / "export_docx.py"
CHECK_DOCX = SKILL_DIR / "scripts" / "check_docx_delivery.py"
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

    def test_docx_export_is_real_and_becomes_stale_after_tex_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docx-export-test-") as temp:
            root = Path(temp)
            main = root / "main.tex"
            section = root / "section.tex"
            section.write_text("补充分析。\n", encoding="utf-8")
            main.write_text(
                "\\documentclass{article}\n"
                "\\usepackage{amsmath}\n"
                "\\begin{document}\n"
                "模型结果：$x^2+y^2=1$.\\\\\n"
                "\\begin{tabular}{cc}A&B\\\\1&2\\end{tabular}\n"
                "\\input{section}\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            docx = root / "exports" / "main.docx"
            export_report = root / "docx_export_report.json"
            process = subprocess.run(
                [sys.executable, str(EXPORT_DOCX), str(main), "--output", str(docx), "--report", str(export_report)],
                text=True, encoding="utf-8", errors="replace", capture_output=True,
            )
            exported = json.loads(export_report.read_text(encoding="utf-8"))
            self.assertIn(exported["status"], {"passed", "unavailable"})
            if exported["status"] == "unavailable":
                self.assertEqual(process.returncode, 2)
                self.assertFalse(docx.exists())
                self.skipTest("Pandoc is unavailable in this environment")

            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertTrue(docx.exists())
            with zipfile.ZipFile(docx) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("补充分析", document_xml)
            delivery_report = root / "docx_delivery_check.json"
            checked = subprocess.run(
                [
                    sys.executable, str(CHECK_DOCX), str(docx), "--source-tex", str(main),
                    "--export-report", str(export_report), "--report", str(delivery_report),
                ],
                text=True, encoding="utf-8", errors="replace", capture_output=True,
            )
            delivery = json.loads(delivery_report.read_text(encoding="utf-8"))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(delivery["status"], "passed_with_visual_check_pending")
            self.assertGreater(delivery["checks"]["non_whitespace_characters"], 0)

            section.write_text("补充分析已在 Overleaf 修改。\n", encoding="utf-8")
            stale = subprocess.run(
                [
                    sys.executable, str(CHECK_DOCX), str(docx), "--source-tex", str(main),
                    "--export-report", str(export_report), "--report", str(delivery_report),
                ],
                text=True, encoding="utf-8", errors="replace", capture_output=True,
            )
            self.assertNotEqual(stale.returncode, 0)
            stale_report = json.loads(delivery_report.read_text(encoding="utf-8"))
            self.assertIn("DOCX mirror is stale relative to the LaTeX source bundle", stale_report["errors"])

    def test_docx_export_reports_unavailable_without_faking_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="docx-unavailable-test-") as temp:
            root = Path(temp)
            main = root / "main.tex"
            main.write_text("\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8")
            docx = root / "main.docx"
            report = root / "report.json"
            environment = dict(os.environ)
            environment["PATH"] = ""
            environment["MODELING_PANDOC"] = str(root / "missing-pandoc")
            process = subprocess.run(
                [sys.executable, str(EXPORT_DOCX), str(main), "--output", str(docx), "--report", str(report)],
                text=True, encoding="utf-8", errors="replace", capture_output=True, env=environment,
            )
            value = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(process.returncode, 2)
            self.assertEqual(value["status"], "unavailable")
            self.assertFalse(docx.exists())


if __name__ == "__main__":
    unittest.main()
