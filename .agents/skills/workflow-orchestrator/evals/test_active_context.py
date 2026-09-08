from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import smoke_case as smoke
import workflow as w


class ActiveContextTest(unittest.TestCase):
    def test_init_generates_deterministic_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-context-init-") as temp:
            root = Path(temp)
            smoke.initialize(root, "lean", "Q1,Q2")
            json_path = root / "planning/context/Q1_active_context.json"
            md_path = root / "planning/context/Q1_active_context.md"
            self.assertTrue(json_path.is_file())
            self.assertTrue(md_path.is_file())
            before_json = json_path.read_bytes()
            before_md = md_path.read_bytes()

            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "workflow.py"), "--workspace", str(root),
                 "context", "--all", "--format", "both"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            result = json.loads(proc.stdout)

            self.assertEqual(result["status"], "GENERATED")
            self.assertEqual(len(result["contexts"]), 2)
            self.assertEqual(before_json, json_path.read_bytes())
            self.assertEqual(before_md, md_path.read_bytes())
            data = json.loads(before_json)
            self.assertEqual(data["canonicality"]["role"], "derived_cache")
            self.assertEqual(data["next_action"]["step"], "problem-frame")
            self.assertIn("planning/workflow_run.json", data["source_sha256"])
            self.assertIn("唯一下一动作", before_md.decode("utf-8"))

    def test_human_decision_is_separated_from_stale_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-context-decision-") as temp:
            root = Path(temp)
            smoke.initialize(root, "lean", "Q1")
            smoke.advance(root, "method-choice")
            args = argparse.Namespace(question="Q1", step="method-choice")
            w.cmd_start(root, args)
            decision = w.cmd_record_decision(
                root,
                argparse.Namespace(
                    **vars(args), choice="accept", selected_method="ols",
                    user_message="采用 OLS，并保留训练均值基线。", rationale=None, rerun_from=None,
                ),
            )["decision"]
            w.append_jsonl(
                root / "methods/Q1/q1_decisions.jsonl",
                {"decision_id": "AI-SUGGESTION", "decision_type": "method_choice", "decided_by": "agent",
                 "status": "DECIDED", "choice": "accept", "selected_method": "random_forest",
                 "user_message": "agent suggestion only", "evidence_hashes": decision["evidence_hashes"]},
            )
            w.cmd_context(root, argparse.Namespace(question="Q1", all=False, format="both"))
            current = w.read_json(root / "planning/context/Q1_active_context.json")
            self.assertEqual([row["decision_id"] for row in current["confirmed_decisions"]], [decision["decision_id"]])
            self.assertEqual(current["methods"]["selected_method"], "ols")
            w.append_jsonl(
                root / "methods/Q1/q1_decisions.jsonl",
                {"decision_id": "AI-SUGGESTION", "decision_type": "method_choice", "status": "DECIDED",
                 "decided_by": "agent", "choice": "accept", "selected_method": "ridge",
                 "user_message": "agent suggestion", "evidence_hashes": decision["evidence_hashes"]},
            )
            w.cmd_context(root, argparse.Namespace(question="Q1", all=False, format="both"))
            filtered = w.read_json(root / "planning/context/Q1_active_context.json")
            self.assertEqual([row["decision_id"] for row in filtered["confirmed_decisions"]], [decision["decision_id"]])

            w.cmd_finish(root, args)
            contract_path = root / "methods/Q1/method_contract.json"
            contract = w.read_json(contract_path)
            contract["main"] = "ridge"
            w.write_json(contract_path, contract)
            w.cmd_context(root, argparse.Namespace(question="Q1", all=False, format="both"))

            stale = w.read_json(root / "planning/context/Q1_active_context.json")
            self.assertFalse(stale["confirmed_decisions"])
            self.assertTrue(any(row.get("decision_id") == decision["decision_id"] for row in stale["stale_or_rejected"]))
            self.assertTrue(any(row.get("node") == "Q1:method-screen" for row in stale["stale_or_rejected"]))
            self.assertEqual(stale["methods"]["contract"]["main"], "ridge")

    def test_pause_and_resume_refresh_the_single_next_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-context-pause-") as temp:
            root = Path(temp)
            smoke.initialize(root, "lean", "Q1")
            initial = w.read_json(root / "planning/context/Q1_active_context.json")
            w.cmd_pause(root, argparse.Namespace(reason="等待用户补充附件"))
            paused = w.read_json(root / "planning/context/Q1_active_context.json")
            self.assertEqual(paused["next_action"]["status"], "PAUSED")
            self.assertEqual(paused["blockers"][0]["kind"], "paused")
            self.assertNotEqual(initial["generated"]["state_sha256"], paused["generated"]["state_sha256"])

            w.cmd_resume(root, argparse.Namespace())
            resumed = w.read_json(root / "planning/context/Q1_active_context.json")
            self.assertEqual(resumed["next_action"]["step"], "problem-frame")
            self.assertEqual(resumed["blockers"], [])

    def test_git_experiment_start_refreshes_active_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="workflow-context-git-") as temp:
            root = Path(temp)
            smoke.initialize(root, "lean", "Q1")
            smoke.advance(root, "method-choice")
            args = argparse.Namespace(question="Q1", step="method-choice")
            w.cmd_start(root, args)
            w.cmd_record_decision(
                root,
                argparse.Namespace(
                    **vars(args), choice="accept", selected_method="ols",
                    user_message="采用 OLS。", rationale=None, rerun_from=None,
                ),
            )
            w.cmd_finish(root, args)

            started = smoke.cli(
                root, smoke.GIT_SCRIPT, "--workspace", str(root), "start",
                "--contest", "smoke", "--question", "Q1", "--algorithm", "ols",
            )
            self.assertEqual(started["context_refresh"]["status"], "GENERATED")
            context = w.read_json(root / "planning/context/Q1_active_context.json")
            self.assertEqual(context["active_experiment"]["active_context"]["branch"], started["branch"])
            self.assertEqual(context["active_experiment"]["experiment_id"], "round1")


if __name__ == "__main__":
    unittest.main()
