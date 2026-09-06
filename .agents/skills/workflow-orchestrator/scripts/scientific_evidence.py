"""Recompute bounded checks from saved split/constraint evidence."""
import json
import math
from datetime import datetime

PREDICTIVE = {"regression", "classification", "forecasting", "time_series"}

def verify(root, data):
    errors = []
    def read(field):
        raw = data.get(field)
        if not isinstance(raw, str):
            raise ValueError(f"missing {field}")
        path = (root / raw).resolve()
        path.relative_to(root.resolve())
        return json.loads(path.read_text(encoding="utf-8-sig"))
    try:
        if data.get("task_type") in PREDICTIVE:
            audit = read("evaluation_audit_file")
            folds = audit.get("folds", [])
            if not folds:
                raise ValueError("evaluation audit requires actual folds")
            for fold in folds:
                train, test = fold.get("train_ids", []), fold.get("evaluation_ids", [])
                if not train or not test or len(set(train)) != len(train) or len(set(test)) != len(test):
                    raise ValueError("empty/duplicate split row IDs")
                if set(train) & set(test):
                    raise ValueError("training/evaluation row overlap")
                if fold.get("preprocessing") == "none":
                    if not fold.get("no_preprocessing_reason"):
                        raise ValueError("explain why no learned preprocessing is needed")
                else:
                    fitted = fold.get("preprocessing_fit_ids", [])
                    if not fitted or not set(fitted) <= set(train):
                        raise ValueError("preprocessing fitted outside training rows or missing fit IDs")
                if data.get("task_type") in {"forecasting", "time_series"}:
                    times = fold.get("target_times", {})
                    origins = fold.get("prediction_origins", {})
                    available = fold.get("feature_available_at", {})
                    stamp = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if max(stamp(times[str(i)]) for i in train) >= min(stamp(times[str(i)]) for i in test):
                        raise ValueError("training targets cross evaluation time boundary")
                    for i in test:
                        key = str(i)
                        if not stamp(available[key]) <= stamp(origins[key]) < stamp(times[key]):
                            raise ValueError("feature/target information unavailable at prediction origin")
        if data.get("task_type") == "optimization":
            audit = read("constraint_audit_file")
            values, tolerance = audit.get("violations"), audit.get("tolerance")
            finite = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
            if not isinstance(values, list) or not values or not finite(tolerance) or tolerance < 0:
                raise ValueError("missing constraint violations/tolerance")
            if any(not finite(x) or x < 0 or x > tolerance for x in values):
                raise ValueError("constraint violation exceeds tolerance")
            if not audit.get("constraint_labels") or len(audit["constraint_labels"]) != len(values):
                raise ValueError("constraint labels must cover every checked residual")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"scientific evidence: {exc}")
    return errors
