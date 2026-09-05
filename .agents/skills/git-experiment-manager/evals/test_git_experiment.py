from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
GIT_SCRIPT = SKILL_DIR / "scripts" / "experiment_git.py"
COMPARE_SCRIPT = SKILL_DIR / "scripts" / "compare_experiments.py"


class GitExperimentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="git-experiment-test-")
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "harness@example.invalid"], cwd=self.root, check=True)
        (self.root / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "baseline.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "baseline"], cwd=self.root, check=True, capture_output=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def call(self, script: Path, *args: str, expected: int = 0) -> dict:
        process = subprocess.run(
            [sys.executable, str(script), *args], cwd=self.root,
            text=True, encoding="utf-8", errors="replace", capture_output=True,
        )
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        return json.loads(process.stdout)

    def make_experiment(self, algorithm: str, round_name: str, value: float) -> tuple[str, Path]:
        started = self.call(
            GIT_SCRIPT, "--workspace", str(self.root), "start",
            "--contest", "smoke", "--question", "Q1", "--algorithm", algorithm,
        )
        code = self.root / "code" / "Q1" / f"{algorithm}.py"
        code.parent.mkdir(parents=True, exist_ok=True)
        code.write_text("""import json, sys
from pathlib import Path
summary, value = sys.argv[1], float(sys.argv[2])
path = Path(summary)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({
    'schema_version': 1, 'status': 'PASSED', 'feasible': True,
    'question_id': 'Q1', 'random_seed': 2026,
    'comparison_contract': {'question_id': 'Q1', 'data_hash': 'data-1',
        'split_hash': 'split-1', 'feature_spec_hash': 'features-1',
        'metric_definition_hash': 'metric-1'},
    'primary_metric': {'name': 'rmse', 'direction': 'minimize', 'value': value},
    'methods': []
}, indent=2))
""", encoding="utf-8")
        code_rel = code.relative_to(self.root).as_posix()
        self.call(GIT_SCRIPT, "--workspace", str(self.root), "checkpoint", "--question", "Q1",
                  "--message", f"exp(q1): implement {algorithm}", "--paths", code_rel)
        summary = self.root / "results" / "Q1" / "experiments" / round_name / "run_summary.json"
        summary_rel = summary.relative_to(self.root).as_posix()
        self.call(GIT_SCRIPT, "--workspace", str(self.root), "run", "--experiment-id", f"Q1-{algorithm}",
                  "--summary", summary_rel, "--code-paths", code_rel, "--", sys.executable, code_rel,
                  summary_rel, str(value))
        recorded = self.call(
            GIT_SCRIPT, "--workspace", str(self.root), "record",
            "--experiment-id", f"Q1-{algorithm}",
            "--summary", summary.relative_to(self.root).as_posix(),
            "--message", f"evidence(q1): record {algorithm}",
        )
        self.assertTrue(recorded["code_commit"])
        self.assertEqual(json.loads(summary.read_text(encoding="utf-8"))["execution"]["code_commit"], recorded["code_commit"])
        return started["branch"], summary

    def add_decision(self, summary: Path, choice: str) -> None:
        relative = summary.relative_to(self.root).as_posix()
        decision = self.root / "methods/Q1/q1_decisions.jsonl"
        decision.parent.mkdir(parents=True, exist_ok=True)
        decision.write_text(json.dumps({
            "schema_version": 1, "decision_id": f"q1_{choice}_{summary.parent.name}",
            "decision_type": "result_verdict", "status": "DECIDED", "decided_by": "human",
            "choice": choice, "user_message": f"test user chooses {choice}", "experiment_id": json.loads(summary.read_text(encoding="utf-8"))["experiment_id"],
            "evidence_hashes": {relative: hashlib.sha256(summary.read_bytes()).hexdigest()},
            "decided_at": "2026-01-01T00:00:00+00:00"
        }) + "\n", encoding="utf-8")

    def test_record_compare_reject_and_accept(self) -> None:
        rejected_branch, left = self.make_experiment("model-a", "round1", 2.0)
        self.add_decision(left, "reject")
        left_relative = left.relative_to(self.root).as_posix()
        rejected = self.call(
            GIT_SCRIPT, "--workspace", str(self.root), "reject",
            "--branch", rejected_branch, "--decision-id", "q1_reject_round1",
        )
        self.assertEqual(rejected["returned_to"], "main")
        branches = subprocess.run(["git", "branch", "--list", rejected_branch], cwd=self.root, text=True, capture_output=True, check=True).stdout
        self.assertIn(rejected_branch, branches)

        with tempfile.TemporaryDirectory(prefix="comparison-fixture-") as compare_temp:
            left_snapshot = Path(compare_temp) / "left.json"
            left_text = subprocess.run(
                ["git", "show", f"{rejected_branch}:{left_relative}"], cwd=self.root,
                text=True, encoding="utf-8", errors="replace", capture_output=True, check=True,
            ).stdout
            left_snapshot.write_text(left_text, encoding="utf-8")

            accepted_branch, right = self.make_experiment("model-b", "round2", 1.5)
            self.add_decision(right, "accept")
            comparison = self.call(COMPARE_SCRIPT, str(left_snapshot), str(right))
            self.assertTrue(comparison["comparable"])
            self.assertEqual(comparison["winner"], "right")

            changed = json.loads(right.read_text(encoding="utf-8"))
            changed["comparison_contract"]["split_hash"] = "different-split"
            mismatch = Path(compare_temp) / "mismatch.json"
            mismatch.write_text(json.dumps(changed), encoding="utf-8")
            incomparable = self.call(COMPARE_SCRIPT, str(left_snapshot), str(mismatch), expected=2)
            self.assertFalse(incomparable["comparable"])

            accepted = self.call(
                GIT_SCRIPT, "--workspace", str(self.root), "accept",
                "--branch", accepted_branch, "--decision-id", "q1_accept_round2",
            )
            self.assertEqual(accepted["base"], "main")
            current = subprocess.run(["git", "branch", "--show-current"], cwd=self.root, text=True, capture_output=True, check=True).stdout.strip()
            self.assertEqual(current, "main")

    def test_checkpoint_rejects_pre_staged_unrelated_file(self) -> None:
        intended = self.root / "model.py"
        unrelated = self.root / "notes.txt"
        intended.write_text("print('model')\n", encoding="utf-8")
        unrelated.write_text("do not include\n", encoding="utf-8")
        subprocess.run(["git", "add", "notes.txt"], cwd=self.root, check=True)
        result = self.call(
            GIT_SCRIPT,
            "--workspace", str(self.root),
            "checkpoint",
            "--question", "Q1",
            "--message", "exp: checkpoint",
            "--paths", "model.py",
            expected=1,
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("index already contains staged changes", result["error"])
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], cwd=self.root,
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        self.assertEqual(staged, "notes.txt")

    def test_record_rejects_outside_summary_before_committing(self) -> None:
        code = self.root / "model.py"
        code.write_text("print('model')\n", encoding="utf-8")
        before = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True, capture_output=True, check=True,
        ).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="outside-summary-") as outside:
            summary = Path(outside) / "summary.json"
            summary.write_text("{}\n", encoding="utf-8")
            result = self.call(
                GIT_SCRIPT,
                "--workspace", str(self.root),
                "record",
                "--experiment-id", "outside",
                "--summary", str(summary),
                "--message", "exp: should not commit",
                "--paths", "model.py",
                expected=1,
            )
        after = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True, capture_output=True, check=True,
        ).stdout.strip()
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("outside workspace", result["error"])
        self.assertEqual(before, after)

    def test_accept_reject_require_experiment_branch(self) -> None:
        result = self.call(
            GIT_SCRIPT,
            "--workspace", str(self.root),
            "reject",
            "--branch", "main",
            "--decision-id", "decision-invalid",
            expected=1,
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("expected an exp/ branch", result["error"])

    def test_compare_rejects_failed_and_nonfinite_runs(self) -> None:
        contract = {
            "question_id": "Q1", "data_hash": "d", "split_hash": "s",
            "feature_spec_hash": "f", "metric_definition_hash": "m"
        }
        left = {"experiment_id": "left", "status": "PASSED", "feasible": True,
                "execution": {"code_commit": "abc"}, "comparison_contract": contract,
                "primary_metric": {"name": "rmse", "direction": "minimize", "value": 1.0}}
        right = json.loads(json.dumps(left))
        right.update(experiment_id="right", status="FAILED", feasible=False)
        right["primary_metric"]["value"] = 0.1
        left_path = self.root / "left.json"
        right_path = self.root / "right.json"
        left_path.write_text(json.dumps(left), encoding="utf-8")
        right_path.write_text(json.dumps(right), encoding="utf-8")
        result = self.call(COMPARE_SCRIPT, str(left_path), str(right_path), expected=2)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["winner"])

        right["status"] = "PASSED"
        right["feasible"] = True
        right["primary_metric"]["value"] = float("nan")
        right_path.write_text(json.dumps(right, allow_nan=True), encoding="utf-8")
        result = self.call(COMPARE_SCRIPT, str(left_path), str(right_path), expected=1)
        self.assertEqual(result["status"], "FAILED")

    def test_timeout_preserves_log_receipt_and_refuses_overwrite(self) -> None:
        code = self.root / "slow.py"
        code.write_text("import time\nprint('started', flush=True)\ntime.sleep(30)\n")
        self.call(GIT_SCRIPT, "--workspace", str(self.root), "checkpoint", "--question", "Q1",
                  "--message", "test slow code", "--paths", "slow.py")
        argv = ("--workspace", str(self.root), "run", "--experiment-id", "timeout1", "--summary",
                "results/Q1/experiments/timeout1/run_summary.json", "--code-paths", "slow.py", "--timeout", "1", "--", sys.executable, "slow.py")
        self.call(GIT_SCRIPT, *argv, expected=1)
        receipt = self.root / "results/Q1/experiments/timeout1/execution_receipt.json"
        before = receipt.read_bytes()
        self.assertEqual(json.loads(before)["status"], "timeout")
        self.assertIn("started", receipt.with_name("execution.log").read_text())
        self.call(GIT_SCRIPT, *argv, expected=1)
        self.assertEqual(receipt.read_bytes(), before)

    def test_failed_launch_preserves_receipt(self) -> None:
        self.call(GIT_SCRIPT, "--workspace", str(self.root), "run", "--experiment-id", "bad",
                  "--summary", "attempt/run_summary.json", "--code-paths", "baseline.txt", "--",
                  "nonexistent-model-runtime-xyz", expected=1)
        receipt = json.loads((self.root / "attempt/execution_receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "failed")
        self.assertTrue(receipt["failure_reason"])


if __name__ == "__main__":
    unittest.main()
