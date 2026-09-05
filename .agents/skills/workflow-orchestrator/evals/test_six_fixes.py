import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import workflow as w
import smoke_case as smoke
from scientific_evidence import verify

spec = importlib.util.spec_from_file_location("presenter", SCRIPTS.parents[1] / "modeling-results-presenter/scripts/present_results.py")
presenter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presenter)

class SixFixTests(unittest.TestCase):
    def test_split_and_constraint_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = {"task_type":"regression", "evaluation_audit_file":"audit.json"}
            self.assertTrue(verify(root, data))
            fold = {"train_ids":[1,2], "evaluation_ids":[3], "preprocessing_fit_ids":[1,2]}
            def save():
                (root / "audit.json").write_text(json.dumps({"folds":[fold]}))
            save()
            self.assertEqual(verify(root, data), [])
            fold["evaluation_ids"] = [2,3]
            save()
            self.assertTrue(verify(root, data))
            fold["evaluation_ids"] = [3]
            fold["preprocessing_fit_ids"] = [1,2,3]
            save()
            self.assertTrue(verify(root, data))
            fold.update(preprocessing_fit_ids=[1,2], target_times={"1":"2026-01-01", "2":"2026-01-02", "3":"2026-01-04"}, prediction_origins={"3":"2026-01-03"}, feature_available_at={"3":"2026-01-02"})
            data["task_type"] = "forecasting"
            save()
            self.assertEqual(verify(root, data), [])
            fold["feature_available_at"]["3"] = "2026-01-04"
            save()
            self.assertTrue(verify(root, data))
            data = {"task_type":"optimization", "constraint_audit_file":"constraints.json"}
            for value, valid in [(0.0, True), (0.1, False), (float("nan"), False)]:
                (root / "constraints.json").write_text(json.dumps({"constraint_labels":["capacity"], "violations":[value], "tolerance":0.001}))
                self.assertEqual(not verify(root, data), valid)

    def test_non_scalar_results_and_omissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            # Reuse the narrative fixture; its sources are generated below.
            run = root / "results/Q1/experiments/round1"
            run.mkdir(parents=True)
            (run / "run_summary.json").write_text(json.dumps({"question_id":"Q1", "experiment_id":"round1", "primary_metric":{"value":1.0}}))
            (run / "estimates.json").write_text(json.dumps({"rmse":1.0, "slope":2.0, "baseline_rmse":3.0}))
            p = smoke.make_presentation(root, "Q1", "round1")
            for raw in p["evidence_files"] + [f for row in p["preparation"] for f in row["evidence_files"]]:
                path = root / raw
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}")
            source = {"path":["A","B","C"], "matrix":[[1,2],[3,4]], "formula":"x = 2t + 1"}
            (root / "values.json").write_text(json.dumps(source))
            (root / "array.json").write_text(json.dumps(source["matrix"]))
            self.assertTrue(w.c.fingerprints(root, ["array.json"])["array.json"])
            (root / "table.csv").write_text("node,value\nA,1\n")
            p.update(assumptions=[], derivations=[], omissions={"assumptions":"题设已给定全部条件", "derivations":"直接求解给定网络"})
            p["results"] = [{"label":k, "type":t, "source_file":"values.json", "source_locator":"/"+k, "value":v, "meaning":"test"} for (k,v),t in zip(source.items(), ["sequence","matrix","formula"])]
            p["results"].append({"label":"table", "type":"table_file", "source_file":"table.csv", "source_sha256":hashlib.sha256((root / "table.csv").read_bytes()).hexdigest(), "meaning":"table"})
            p["conclusions"] = [{"text":"路径经过 B", "scope":"给定图", "result_labels":["path"]}]
            self.assertIn("A", presenter.render(root, p))
            p["results"][0]["value"] = ["A","C"]
            with self.assertRaises(ValueError):
                presenter.validate(root, p)
            p["results"][0]["value"] = source["path"]
            (root / "table.csv").write_text("changed")
            with self.assertRaises(ValueError):
                presenter.validate(root, p)

    def test_decision_and_new_experiment_handoff(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            smoke.initialize(root, "lean", "Q1")
            smoke.advance(root, "method-choice")
            args = argparse.Namespace(question="Q1", step="method-choice")
            w.cmd_start(root, args)
            row = w.cmd_record_decision(root, argparse.Namespace(**vars(args), choice="accept", selected_method="ols", user_message="同意采用 OLS", rationale=None, rerun_from=None))["decision"]
            self.assertIsNone(row["rationale"])
            self.assertTrue(row["evidence_hashes"])
            w.cmd_finish(root, args)
            smoke.advance(root, "result-verdict")
            old = root / "results/Q1/experiments/round1/run_summary.json"
            before = old.read_bytes()
            args.step = "result-verdict"
            w.cmd_start(root, args)
            w.cmd_record_decision(root, argparse.Namespace(**vars(args), choice="adjust", selected_method=None, user_message="调整实现后再运行", rationale=None, rerun_from="model-run"))
            result = w.cmd_finish(root, args)
            self.assertEqual(result["next"]["step"], "git-experiment")
            self.assertEqual(old.read_bytes(), before)
            eid = w.read_json(root / "planning/workflow_run.json")["iterations"]["Q1"]
            summary = f"results/Q1/experiments/{eid}/run_summary.json"
            proc = subprocess.run([sys.executable, str(smoke.GIT_SCRIPT), "--workspace", str(root), "run", "--experiment-id", eid, "--summary", summary, "--code-paths", "code/model.py", "--", sys.executable, "code/model.py", "Q1", eid], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("context", proc.stdout)
            # Isolated fixture only: save all generated test state before a real branch transition.
            subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "test: preserve previous attempt"], cwd=root, check=True, capture_output=True)
            smoke.cli(root, smoke.GIT_SCRIPT, "--workspace", str(root), "start", "--contest", "smoke", "--question", "Q1", "--algorithm", eid, "--from-current")
            args.step = "git-experiment"
            w.cmd_start(root, args)
            w.cmd_finish(root, args)
            smoke.advance(root, "result-verdict")
            self.assertTrue((root / summary).is_file())
            self.assertEqual(old.read_bytes(), before)

if __name__ == "__main__":
    unittest.main()
