from __future__ import annotations

import argparse
import importlib.util
import json
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
    def test_profiles_resolve_from_one_pipeline(self) -> None:
        assets = SCRIPT.parent.parent / "assets"
        pipeline = json.loads((assets / "pipeline.template.json").read_text(encoding="utf-8"))
        submission_spec = json.loads((assets / "cumcm-submission.template.json").read_text(encoding="utf-8"))
        lean_spec = json.loads((assets / "lean.template.json").read_text(encoding="utf-8"))
        self.assertNotIn("human_checkpoints", pipeline)
        self.assertNotIn("steps", submission_spec)
        self.assertNotIn("steps", lean_spec)

        submission = workflow.load_template("submission")
        lean = workflow.load_template("lean")
        self.assertEqual(len(submission["steps"]), 17)
        self.assertEqual(len(lean["steps"]), 16)
        expected_pauses = {
            "material_framing_ambiguity", "final_method_choice",
            "result_accept_adjust_or_fallback",
        }
        for template in (submission, lean):
            reasons = {step["checkpoint"]["reason"] for step in template["steps"] if step.get("checkpoint")}
            self.assertEqual(reasons, expected_pauses)

    def test_runtime_config_uses_flat_session_fields_only(self) -> None:
        template = workflow.load_template("submission")
        session = {
            "robustness_required": False,
            "detailed_code_plan": True,
            "notes": ["metadata"],
            "execution_policy": {"robustness_required": True},
        }
        config = workflow.resolved_config(Path.cwd(), argparse.Namespace(), session, template)
        self.assertFalse(config["robustness_required"])
        self.assertTrue(config["detailed_code_plan"])
        self.assertNotIn("notes", config)
        self.assertNotIn("execution_policy", config)

    def test_template_driven_smoke(self) -> None:
        result = workflow.smoke_test()
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["runtime_check"], "PASSED")
        self.assertEqual(result["rerun_next"], "model-run")
        self.assertIn("final_method_choice", result["observed_path_pauses"])

    def test_language_variant_and_terminal_step(self) -> None:
        template = workflow.load_template("submission")
        python_steps = workflow.applicable_steps(template, {"implementation_language": "python"})
        matlab_steps = workflow.applicable_steps(template, {"implementation_language": "matlab"})
        self.assertEqual(python_steps[-1]["id"], "solution-presentation")
        matlab_run = next(step for step in matlab_steps if step["id"] == "model-run")
        self.assertEqual(matlab_run["skill"], "matlab-model-code-generator")

    def test_upstream_rerun_has_no_paper_freeze_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-rerun-test-") as temp:
            workspace = Path(temp)
            init_git(workspace)
            workflow.cmd_init(
                workspace,
                argparse.Namespace(
                    profile="submission",
                    questions="Q1",
                    contest="CUMCM",
                    language="python",
                    seed=2026,
                    workflow_id="rerun-test",
                    allow_no_git=False,
                ),
            )
            result = workflow.cmd_rerun(
                workspace, argparse.Namespace(question="Q1", from_step="problem-frame", new_run=False, new_branch=False)
            )
            manifest = workflow.load_manifest(workspace, "Q1")
            self.assertEqual(result["next"]["step"], "problem-frame")
            self.assertNotIn("freeze_state", manifest)

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

if __name__ == "__main__":
    unittest.main()
