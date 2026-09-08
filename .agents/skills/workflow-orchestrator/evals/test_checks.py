from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CHECKS = Path(__file__).resolve().parents[1] / "scripts" / "checks"


def run_check(name: str, *args: str, cwd: Path) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(CHECKS / name), *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    return completed.returncode, json.loads(completed.stdout)


class DeterministicChecksTest(unittest.TestCase):
    def test_leakage_check_rejects_random_time_split_and_global_fit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="check-leakage-") as temp:
            root = Path(temp)
            contract = root / "contract.json"
            contract.write_text(
                json.dumps(
                    {
                        "task_type": "time_series",
                        "split": {"strategy": "random"},
                        "preprocessing": {"fit_scope": "global"},
                    }
                ),
                encoding="utf-8",
            )
            code, report = run_check("leakage_check.py", str(contract), cwd=root)
            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "FAILED")
            self.assertGreaterEqual(len(report["errors"]), 2)

    def test_method_reference_check_accepts_optional_reference_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="check-reference-") as temp:
            root = Path(temp)
            summary = root / "run_summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "methods": [
                            {"role": "main", "status": "success", "metrics_summary": {"rmse": 1.0}, "output_files": ["results.json"]},
                            {"role": "empirical_baseline", "status": "success", "metrics_summary": {"rmse": 1.4}, "output_files": ["results.json"]},
                        ],
                        "comparison_contract": {
                            "data_hash": "d",
                            "split_hash": "s",
                            "feature_spec_hash": "f",
                            "metric_definition_hash": "m",
                        },
                        "comparison": {"comparable": True},
                        "primary_metric": {"name": "rmse", "direction": "minimize"},
                    }
                ),
                encoding="utf-8",
            )
            method = root / "method_contract.json"
            method.write_text(json.dumps({"reference_policy": {"role": "empirical_baseline", "required": True}}), encoding="utf-8")
            code, report = run_check("method_reference_check.py", str(summary), "--method-contract", str(method), cwd=root)
            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "PASSED")

    def test_frozen_number_check_verifies_source_locator_and_decision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="check-freeze-") as temp:
            root = Path(temp)
            source = root / "results.json"
            source.write_text(json.dumps({"metrics": {"rmse": 1.25}}), encoding="utf-8")
            freeze = root / "frozen.json"
            freeze.write_text(
                json.dumps(
                    {
                        "claims": [
                            {
                                "claim_id": "q1_rmse",
                                "value": 1.25,
                                "source_file": "results.json",
                                "source_locator": "$.metrics.rmse",
                                "decision_id": "decision-1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            code, report = run_check(
                "frozen_number_check.py", str(freeze), "--workspace", str(root), cwd=root
            )
            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "PASSED")

    def test_artifact_check_rejects_paths_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="check-artifact-") as temp:
            root = Path(temp)
            code, report = run_check(
                "artifact_check.py",
                "--workspace",
                str(root),
                "--paths",
                str(root.parent / "outside.json"),
                cwd=root,
            )
            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "FAILED")
            self.assertIn("outside workspace", report["errors"][0])


if __name__ == "__main__":
    unittest.main()
