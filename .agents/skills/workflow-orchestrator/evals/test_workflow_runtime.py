from __future__ import annotations

import argparse
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workflow.py"
SPEC = importlib.util.spec_from_file_location("workflow_runtime", SCRIPT)
assert SPEC and SPEC.loader
workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workflow)


def init_git(workspace: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "harness@example.invalid"], cwd=workspace, check=True)
    (workspace / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=workspace, check=True, capture_output=True)


class WorkflowRuntimeTest(unittest.TestCase):
    def test_template_driven_smoke(self) -> None:
        result = workflow.smoke_test()
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["runtime_check"], "PASSED")
        self.assertEqual(result["rerun_next"], "model-run")
        self.assertIn("final_method_choice", result["observed_path_pauses"])

    def test_paper_and_language_variants(self) -> None:
        template = workflow.load_template("submission")
        dual_latex = workflow.applicable_steps(template, {
            "paper_format": "latex", "delivery_mode": "latex_primary_docx_mirror",
            "implementation_language": "python",
        })
        single_latex = workflow.applicable_steps(template, {
            "paper_format": "latex", "delivery_mode": "single", "implementation_language": "python",
        })
        word = workflow.applicable_steps(template, {
            "paper_format": "word", "delivery_mode": "single", "implementation_language": "python",
        })
        markdown = workflow.applicable_steps(template, {
            "paper_format": "markdown", "delivery_mode": "single", "implementation_language": "python",
        })
        matlab = workflow.applicable_steps(template, {
            "paper_format": "latex", "delivery_mode": "single", "implementation_language": "matlab",
        })
        self.assertIn("latex-build", {step["id"] for step in dual_latex})
        self.assertIn("docx-export", {step["id"] for step in dual_latex})
        self.assertNotIn("docx-export", {step["id"] for step in single_latex})
        self.assertIn("word-build", {step["id"] for step in word})
        self.assertIn("markdown-build", {step["id"] for step in markdown})
        self.assertNotIn("latex-build", {step["id"] for step in word})
        word_section = next(step for step in word if step["id"] == "paper-section")
        self.assertEqual(word_section["outputs"], ["paper/sections/{question_lower}.md"])
        matlab_run = next(step for step in matlab if step["id"] == "model-run")
        self.assertEqual(matlab_run["skill"], "matlab-model-code-generator")

    def test_upstream_rerun_before_freeze_does_not_require_thaw(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-rerun-test-") as temp:
            workspace = Path(temp)
            init_git(workspace)
            workflow.cmd_init(
                workspace,
                argparse.Namespace(
                    profile="submission",
                    questions="Q1",
                    contest="CUMCM",
                    paper_format="latex",
                    delivery_mode="latex_primary_docx_mirror",
                    language="python",
                    seed=2026,
                    workflow_id="rerun-test",
                    allow_no_git=False,
                ),
            )
            result = workflow.cmd_rerun(
                workspace, argparse.Namespace(question="Q1", from_step="problem-parse")
            )
            manifest = workflow.load_manifest(workspace, "Q1")
            self.assertEqual(result["next"]["step"], "problem-parse")
            self.assertNotEqual(manifest.get("freeze_state"), "thaw_required")

    def test_pause_and_resume_are_persistent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-pause-test-") as temp:
            workspace = Path(temp)
            init_git(workspace)
            workflow.cmd_init(
                workspace,
                argparse.Namespace(
                    profile="lean",
                    questions="Q1,Q2",
                    contest="CUMCM",
                    paper_format="none",
                    delivery_mode="single",
                    language="auto",
                    seed=2026,
                    workflow_id="pause-test",
                    allow_no_git=False,
                ),
            )
            workflow.cmd_pause(workspace, argparse.Namespace(reason="human requested pause"))
            paused = workflow.cmd_next(workspace, argparse.Namespace(question=None))
            self.assertEqual(paused["status"], "PAUSED")
            workflow.cmd_resume(workspace, argparse.Namespace())
            resumed = workflow.cmd_next(workspace, argparse.Namespace(question=None))
            self.assertEqual(resumed["status"], "READY")
            self.assertEqual(resumed["question_id"], "Q1")

    def test_docx_delivery_step_invalidates_when_tex_bundle_changes(self) -> None:
        template = workflow.load_template("submission")
        steps = workflow.applicable_steps(template, {
            "paper_format": "latex",
            "delivery_mode": "latex_primary_docx_mirror",
            "implementation_language": "python",
        })
        step = next(item for item in steps if item["id"] == "docx-export")
        with tempfile.TemporaryDirectory(prefix="workflow-docx-stale-") as temp:
            workspace = Path(temp)
            (workspace / "paper" / "sections").mkdir(parents=True)
            (workspace / "paper" / "main.tex").write_text("main\n", encoding="utf-8")
            section = workspace / "paper" / "sections" / "q1.tex"
            section.write_text("version one\n", encoding="utf-8")
            workflow.create_smoke_output(workspace, step, "Q1")
            manifest = {"question_id": "Q1", "steps": {}}
            self.assertTrue(workflow.step_complete(workspace, manifest, step))
            section.write_text("version two\n", encoding="utf-8")
            self.assertFalse(workflow.step_complete(workspace, manifest, step))


if __name__ == "__main__":
    unittest.main()
