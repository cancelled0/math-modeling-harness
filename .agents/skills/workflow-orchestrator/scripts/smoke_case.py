"""Real deterministic numerical integration fixture. Human choices are TEST fixtures.

Exercises the installed workflow through section writing; publication/visual approval
is intentionally left pending unless a separate real rendering review is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import workflow as w

GIT_SCRIPT = w.SKILL_DIR.parent / "git-experiment-manager/scripts/experiment_git.py"
PRESENTER = w.SKILL_DIR.parent / "modeling-results-presenter/scripts/present_results.py"

MODEL = r'''
import csv, json, math, hashlib, sys
from pathlib import Path
q, experiment = sys.argv[1:]
root = Path.cwd()
data_file = root / "workspace/data/clean.csv"
rows = [(float(r["x"]), float(r["y"])) for r in csv.DictReader(data_file.open())]
train, test = rows[:12], rows[12:]
xs, ys = zip(*train)
xbar, ybar = sum(xs)/len(xs), sum(ys)/len(ys)
slope = sum((x-xbar)*(y-ybar) for x,y in train)/sum((x-xbar)**2 for x in xs)
intercept = ybar-slope*xbar
if q == "Q2":
    prior = json.loads((root / "results/Q1/experiments/round1/estimates.json").read_text())
    slope, intercept = prior["slope"], prior["intercept"]
pred = [slope*x+intercept for x,y in test]
main = math.sqrt(sum((p-y)**2 for p,(_,y) in zip(pred,test))/len(test))
baseline = math.sqrt(sum((ybar-y)**2 for x,y in test)/len(test))
folder = root / f"results/{q}/experiments/{experiment}"
folder.mkdir(parents=True,exist_ok=True)
output = folder / "estimates.json"
output.write_text(json.dumps({"slope":slope,"intercept":intercept,"rmse":main,"baseline_rmse":baseline,"prediction_last":pred[-1]}))
rel = output.relative_to(root).as_posix()
h = lambda b: hashlib.sha256(b).hexdigest()
contract = {"question_id":q,"data_hash":h(data_file.read_bytes()),"split_hash":h(b"first12/rest"),"feature_spec_hash":h(b"x"),"metric_definition_hash":h(b"rmse"),"target_hash":h(b"y"),"evaluation_rows_hash":h(b"12:20"),"population_hash":h(b"synthetic")}
methods = [{"method_id":name,"role":role,"status":"success","metrics_summary":{"rmse":value},"output_files":[rel],"degeneracy_check":{"status":"passed","reason":"slope nonzero; predictions vary"}} for name,role,value in [("ols","main",main),("mean","usable_baseline",baseline)]]
task = "regression" if q == "Q1" else "forecasting"
checks = ["heldout_evaluation"] if q == "Q1" else ["temporal_split","availability_time"]
summary = {"schema_version":1,"status":"PASSED","question_id":q,"experiment_id":experiment,"random_seed":2026,"task_type":task,"feasible":True,"primary_metric":{"name":"rmse","value":main,"direction":"minimize"},"methods":methods,"comparison_contract":contract,"split":{"strategy":"temporal"},"preprocessing":{"fit_scope":"train"},"scientific_checks":{key:{"status":"passed","evidence_files":[rel]} for key in checks},"input_files":["workspace/data/clean.csv"],"fallback_trigger":{"triggered":False}}
(folder / "run_summary.json").write_text(json.dumps(summary,indent=2))
'''


def json_file(root, raw, data):
    w.write_json(root / raw, data)


def text_file(root, raw, text):
    path = root / raw
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def cli(root, script, *args):
    proc = subprocess.run([sys.executable, str(script), *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode:
        raise AssertionError(proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


def initialize(root, profile="lean", questions="Q1,Q2"):
    for args in (("init", "-b", "main"), ("config", "user.name", "Harness Test"), ("config", "user.email", "harness@example.invalid")):
        subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    text_file(root, "code/model.py", MODEL)
    text_file(root, "workspace/data/clean.csv", "x,y\n" + "".join(f"{i},{2*i+1+(i%3-1)*0.1}\n" for i in range(20)))
    subprocess.run(["git", "add", "code/model.py", "workspace/data/clean.csv"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "test: deterministic numerical model"], cwd=root, capture_output=True, check=True)
    json_file(root, "planning/session_config.json", {"question_dependencies": {"Q2": ["Q1"]} if "Q2" in questions else {}})
    w.cmd_init(root, argparse.Namespace(profile=profile, questions=questions, paper_format="markdown" if profile == "submission" else "none", language="python", allow_no_git=False))


def make_presentation(root, q, iteration):
    run_path = f"results/{q}/experiments/{iteration}/run_summary.json"
    run = w.read_json(root / run_path)
    result_path = f"results/{q}/experiments/{iteration}/estimates.json"
    estimates = w.read_json(root / result_path)
    return {
        "schema_version": 1, "status": "ready_for_review", "question_id": q, "experiment_id": iteration,
        "title": "合成线性数据的参数估计与外推（测试示例）", "problem_goal": "估计输入与响应的线性关系，并评价留出数据上的预测误差。", "run_summary": run_path,
        "assumptions": [{"id": "A1", "statement": "在测试范围内，响应的条件均值可由线性关系近似。", "basis": "本例由已知线性生成过程构造；真实赛题需检验。", "impact": "若出现结构变化，外推可能失效。", "validation": "使用末尾八个样本留出检验。"}],
        "preparation": [{"text": "保留前十二个样本用于拟合，后八个样本只用于评价；均值基线也仅使用训练数据。", "evidence_files": ["workspace/data/clean.csv", run_path]}],
        "derivations": [{"id": "D1", "statement": "最小二乘估计可由正规方程得到。", "derivation": "令 S(a,b)=Σ(yᵢ-a-bxᵢ)²。令两偏导为零，得 b=Σ(xᵢ-x̄)(yᵢ-ȳ)/Σ(xᵢ-x̄)²，a=ȳ-bx̄。", "conditions": "训练输入方差非零；该代数结论不等于证明样本外预测一定准确。"}],
        "model": {"name": "带截距的一元线性回归", "rationale": "测试数据具有已知近似线性结构，模型参数少、含义清楚，可直接检查外推误差。", "formulation": "yᵢ=a+bxᵢ+εᵢ；最小化训练残差平方和。", "variables": "x 为无量纲输入，y 为无量纲响应，a 为截距，b 为斜率。", "constraints": "a、b 为实数；训练 x 不能全部相同。", "alternatives": "训练响应均值作为可用基线；本例不需要增加非线性模型。"},
        "algorithm": {"name": "解析最小二乘解", "steps": ["计算训练均值和离差平方和。", "计算斜率、截距；Q2 复用 Q1 参数。", "在相同留出样本上计算主模型和均值基线 RMSE。"], "parameters": "训练样本数为 12；数据生成规则固定。", "stopping_rule": "闭式计算完成，无迭代停止阈值。", "reproducibility": f"执行已提交的 code/model.py {q} {iteration}；实际提交见运行摘要。"},
        "results": [{"label": "留出RMSE", "source_file": run_path, "source_locator": "$.primary_metric.value", "value": run["primary_metric"]["value"], "unit": "无量纲", "meaning": "衡量留出样本上的预测误差，越小越好。"},
                    {"label": "斜率", "source_file": result_path, "source_locator": "$.slope", "value": estimates["slope"], "unit": "无量纲", "meaning": "输入增加一单位时线性预测的变化量。"}],
        "conclusions": [{"text": "在本组合成数据上，线性模型的留出误差小于训练均值基线；该结论不能推广到任意真实数据。", "scope": "当前生成规则、训练区间和留出区间。", "result_labels": ["留出RMSE", "斜率"]}],
        "diagnostics": {"baseline_comparison": f"均值基线 RMSE={estimates['baseline_rmse']}，主模型 RMSE={estimates['rmse']}，采用同一留出数据。", "robustness": "改变训练窗口长度进行稳定性检查，见鲁棒性摘要。", "limitations": "数据为确定性合成例；未证明因果关系，也未验证真实场景中的结构变化。"},
        "evidence_files": [run_path, result_path, f"methods/{q}/{q.lower()}_foundations.json", f"robustness/{q}/{q.lower()}_robustness_summary.json"]}


def produce(root, action, choice="accept"):
    q, sid = action["question_id"], action["step"]
    run, template = w.load_runtime(root)
    iteration = run["iterations"].get(q, "round1")
    nodes = w.graph(root, run, template)
    step = nodes[action.get("node", f"{q}:{sid}")]
    out = step["outputs"]
    summary = f"results/{q}/experiments/{iteration}/run_summary.json"
    if sid == "problem-parse":
        json_file(root, out[0], {"subquestions": run["questions"], "material_ambiguities": [], "input_files": ["workspace/data/clean.csv"]})
    elif sid == "framing-check":
        pass
    elif sid == "problem-classify":
        json_file(root, out[0], {"subquestions": {x: "regression" if x == "Q1" else "forecasting" for x in run["questions"]}})
    elif sid == "data-audit":
        json_file(root, out[0], {"data_mode": "synthetic_test", "input_files": ["workspace/data/clean.csv"], "quality_findings": ["20 rows, fixed units, no missing values"]})
        json_file(root, out[1], {"sources": [], "reason": "explicit synthetic integration test; no external data"})
    elif sid == "academic-evidence-scan":
        json_file(root, out[0], {"search_log": [{"query": "synthetic OLS fixture", "provider": "test fixture, no external search", "searched_at": w.now(), "outcome": "no external source required for known synthetic formula"}], "findings": [], "gaps": ["not a real literature search"], "stop_reason": "isolated numerical integration test"})
    elif sid == "method-screen":
        text_file(root, out[0], "Use OLS with training-mean baseline; known synthetic linear generator.\n")
        json_file(root, out[1], {"status": "passed", "finding": "training x variance is positive"})
        json_file(root, out[2], {"main": "ols", "usable_baseline": "training_mean", "rationale": "known linear synthetic structure", "task_type": "regression", "required_checks": ["heldout_evaluation"]})
    elif sid == "git-experiment":
        # Real experiment branch. Keep each question's numerical artifacts in its own folder.
        branch = w.git_context(root)["branch"]
        if not branch.startswith("exp/"):
            cli(root, GIT_SCRIPT, "--workspace", str(root), "start", "--contest", "smoke", "--question", q, "--algorithm", "ols")
        json_file(root, out[0], {"branch": w.git_context(root)["branch"], "parent_commit": w.git_context(root)["commit"], "question_id": q})
    elif sid == "model-foundations":
        json_file(root, out[0], {"assumptions": ["linear conditional mean"], "symbols": {"x": "input", "y": "response"}, "preparation": ["fixed training/test split"], "derivations": ["OLS normal equations"]})
    elif sid == "code-plan":
        text_file(root, out[0], "Execute committed code/model.py; train first 12 rows, evaluate remaining 8; compare mean baseline.\n")
    elif sid == "model-run":
        cli(root, GIT_SCRIPT, "--workspace", str(root), "run", "--experiment-id", iteration, "--summary", summary,
            "--code-paths", "code/model.py", "--inputs", "workspace/data/clean.csv", "--", sys.executable, "code/model.py", q, iteration)
    elif sid == "code-review":
        json_file(root, out[0], {"status": "passed", "evidence_files": [summary, "code/model.py"], "checks": {"heldout": "first12/rest", "preprocessing": "train_only"}})
    elif sid == "result-report":
        values = w.read_json(root / summary)["primary_metric"]
        text_file(root, out[0], f"Heldout {values['name']} = {values['value']}; compare training mean in run summary.\n")
    elif sid == "robustness":
        # Refit several actual windows; no fabricated sensitivity metric.
        import csv
        from statistics import linear_regression
        with (root / "workspace/data/clean.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        slopes = [linear_regression([float(r['x']) for r in rows[:n]], [float(r['y']) for r in rows[:n]]).slope for n in (9, 10, 11, 12)]
        json_file(root, out[0], {"status": "passed", "evidence_files": [summary, "workspace/data/clean.csv"], "findings": {"window_slopes": slopes, "range": max(slopes)-min(slopes)}, "limitations": "synthetic generator only"})
    elif sid == "results-presentation":
        json_file(root, out[0], make_presentation(root, q, iteration))
        cli(root, PRESENTER, "--workspace", str(root), "--spec", out[0], "--index")
    elif sid == "method-explanation":
        text_file(root, out[0], (root / f"results/{q}/experiments/{iteration}/presentation.md").read_text(encoding="utf-8"))
    elif sid == "freeze":
        value = w.read_json(root / summary)["primary_metric"]["value"]
        text_file(root, out[0], "Accepted synthetic OLS evidence; no claims beyond this generated dataset.\n")
        json_file(root, out[1], {"claims": [{"claim_id": "rmse", "value": value, "source_file": summary, "source_locator": "$.primary_metric.value", "decision_id": f"TEST-{q}-package_signoff"}]})
    elif sid == "figure-plan":
        text_file(root, out[0], "This small integration fixture uses numeric results; no figure is necessary.\n")
    elif sid == "figures":
        json_file(root, out[0], {"status": "passed", "figures": [], "omission_reason": "small numerical fixture has no figure requirement"})
    elif sid == "paper-section":
        text_file(root, out[0], (root / f"results/{q}/experiments/{iteration}/presentation.md").read_text(encoding="utf-8"))
    elif sid == "paper-polish":
        source = root / f"paper/drafts/{q.lower()}.md"
        if not source.exists():
            source = root / f"paper/sections/{q.lower()}.md"
        text_file(root, out[0], source.read_text(encoding="utf-8"))
    elif sid == "references":
        text_file(root, out[0], "% Synthetic numerical fixture; no external references claimed.\n")
        text_file(root, out[1], "No external citations in synthetic fixture.\n")
        json_file(root, out[2], {"status": "passed", "evidence_files": [f"paper/sections/{x.lower()}.md" for x in run["questions"]], "unresolved": []})
    elif not step.get("checkpoint"):
        raise ValueError(f"fixture producer intentionally stops before real publication: {sid}")
    if step.get("checkpoint"):
        dtype = step["checkpoint"]["decision_type"]
        relative = w.render(step["checkpoint"].get("decision_file", f"methods/{q}/{q.lower()}_decisions.jsonl"), q)
        row = {"decision_id": f"TEST-{q}-{dtype}", "decision_type": dtype, "decided_by": "human", "status": "DECIDED", "choice": choice,
            "user_message": "TEST FIXTURE ONLY: accept the synthetic scenario", "rationale": "test fixture", "decided_at": w.now(), "experiment_id": iteration,
            "evidence_hashes": w.binding(root, step, nodes)}
        if dtype == "method_choice":
            row["selected_method"] = "ols"
        w.append_jsonl(root / relative, row)


def advance(root, stop_before=None, max_steps=120):
    sequence, pauses = [], []
    for _ in range(max_steps):
        action = w.cmd_next(root, argparse.Namespace(question=None))
        if action["status"] == "COMPLETE" or action.get("step") == stop_before:
            return sequence, pauses, action
        if action["status"] != "READY":
            raise AssertionError(action)
        if action.get("checkpoint"):
            pauses.append(action["checkpoint"]["reason"])
        args = argparse.Namespace(question=action["question_id"], step=action["step"])
        w.cmd_start(root, args)
        produce(root, action)
        w.cmd_finish(root, args)
        sequence.append(f"{action['question_id']}:{action['step']}")
    raise AssertionError("workflow failed to converge")


def run_smoke():
    with tempfile.TemporaryDirectory(prefix="modeling-numerical-smoke-") as temp:
        root = Path(temp)
        initialize(root, "submission")
        sequence, pauses, pending = advance(root, "markdown-build")
        assert sequence.index("Q1:result-verdict") < sequence.index("Q2:method-screen")
        assert sequence.index("Q1:results-presentation") < sequence.index("Q1:result-verdict")
        assert pending["step"] == "markdown-build"
        values = {q: w.read_json(root / f"results/{q}/experiments/round1/run_summary.json")["primary_metric"]["value"] for q in ("Q1", "Q2")}
        changed = root / "workspace/data/clean.csv"
        changed.write_text(changed.read_text() + "20,41\n")
        state = w.cmd_status(root, argparse.Namespace(question=None))
        assert all(not q["allowed"]["paper_writing"] for q in state["questions"])
        return {"status": "PASSED", "runtime_check": "PASSED", "rerun_next": "model-run", "scope": "real two-question computation, receipts, presentation, decisions, freeze and paper sections",
                "steps": sequence, "observed_path_pauses": pauses, "metrics": values, "upstream_mutation_invalidated": True,
                "publication": "NOT TESTED HERE: real PDF/DOCX rendering and visual review remain separate acceptance tests"}
