---
name: forecasting-single-series
description: >
  Forecasts a single time series using ForecasterRecursive or ForecasterDirect.
  Covers data preparation, model creation, training, prediction, backtesting,
  and prediction intervals. Use when the user needs to predict future values
  of one time series.
---

公共规则统一遵循 [项目 AGENTS.md](../../../AGENTS.md)；本 Skill 仅补充专业操作与产物契约。

# Forecasting a Single Time Series

## When to Use

Use this workflow when you have **one time series** and want to predict its future values.

- **ForecasterRecursive**: Default choice. Uses its own predictions as inputs for multi-step forecasting. Works with any sklearn-compatible regressor.
- **ForecasterDirect**: Trains one model per forecast step. Better when the relationship between lags and target changes across the horizon.

### Related skills

- **Before full implementation**: `method-selector` records a recursive/direct or statistical-family choice and a usable time-series baseline; the human approves the final method at G2.5.
- **Feature contract**: `feature-engineering` assembles lag, rolling, calendar, and exogenous features after the chronological split and records their availability time.
- **ACF/PACF and ARIMA diagnostics**: use `statsmodels` when these diagnostics are relevant; do not require them for every estimator.
- **Estimator pipeline and tuning**: use `scikit-learn`, fitting preprocessing and tuning only inside chronological training folds.
- **Intervals and stability**: use the interval support in this workflow, then verify coverage, window sensitivity, and drift with `robustness-checker`.
- **Required baseline**: always run a task-completing seasonal-naive, last-value, moving-average, or simple statistical baseline on the same backtest windows and metrics.

## Stop Conditions

Scan before writing code. Each row lists a rule, the symptom when it is broken, and the recovery. For failures outside this table, return to `result-report-generator` for data/feature/method/parameter/implementation/metric diagnosis.

| Rule | Symptom | Recovery |
|------|---------|----------|
| Set the index frequency before fitting | `ValueError: ... must be a DatetimeIndex with frequency` | Call `data = data.asfreq('h')` (or the correct alias) on `y` and `exog` |
| `exog` passed to `predict()` must cover every future step | `exog` length / index error, or the forecast stops short | Slice exog to the full horizon: one row per step, dates matching the forecast |
| Fit with `store_in_sample_residuals=True` before `predict_interval(method='bootstrapping')` | `No in-sample residuals stored` / empty residuals | Refit: `forecaster.fit(y=y_train, store_in_sample_residuals=True)` |
| Split chronologically, never shuffle | Over-optimistic metrics, leakage | Use a time-ordered split (`TimeSeriesFold`); do not random-split |

## Complete Workflow

The example below illustrates the library mechanics. In a contest workspace, first honor the approved method card, baseline, feature spec, code plan, and experiment paths rather than copying filenames or parameters literally.

```python
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from skforecast.recursive import ForecasterRecursive
from skforecast.preprocessing import RollingFeatures
from skforecast.model_selection import backtesting_forecaster, TimeSeriesFold

# 1. Load and prepare data (MUST have DatetimeIndex with frequency)
data = pd.read_csv('data.csv', index_col='date', parse_dates=True)
data = data.asfreq('h')  # Set frequency — required

# 2. Train/test split (time-based, never random)
end_train = '2023-01-01'
y_train = data.loc[:end_train, 'target']
y_test = data.loc[end_train:, 'target']

# 3. Create forecaster with optional rolling features
rolling_features = RollingFeatures(
    stats=['mean', 'std'],
    window_sizes=24
)

forecaster = ForecasterRecursive(
    estimator=RandomForestRegressor(n_estimators=100, random_state=123),
    lags=24,
    window_features=rolling_features,
    transformer_y=None,          # e.g., StandardScaler() for scaling
    categorical_features='auto', # Auto-detect and encode non-numeric exog columns
    differentiation=None,        # e.g., 1 for first-order differencing
    dropna_from_series=False,    # True to drop NaN rows; False to keep (NaN-tolerant estimators)
)

# 4. Train
forecaster.fit(y=y_train)

# 5. Predict
predictions = forecaster.predict(steps=10)

# 6. Backtesting (proper evaluation)
cv = TimeSeriesFold(
    steps=10,
    initial_train_size=len(y_train),
    refit=False,
    fixed_train_size=False,
)

metric, predictions_bt = backtesting_forecaster(
    forecaster=forecaster,
    y=data['target'],
    cv=cv,
    metric='mean_absolute_error',
)
print(f"MAE: {metric}")

# 7. Prediction intervals
# Default interval is [0.05, 0.95] (90%). Here [0.1, 0.9] creates an 80% interval.
forecaster.fit(y=y_train, store_in_sample_residuals=True)
predictions_interval = forecaster.predict_interval(
    steps=10,
    interval=[0.1, 0.9],        # 80% prediction interval (quantiles, 0-1 scale)
    method='bootstrapping',
    n_boot=500,
)
```

## With Exogenous Variables

```python
# Exogenous variables must cover the forecast horizon during prediction
forecaster = ForecasterRecursive(
    estimator=RandomForestRegressor(n_estimators=100, random_state=123),
    lags=24,
)
forecaster.fit(y=y_train, exog=exog_train)
predictions = forecaster.predict(steps=10, exog=exog_test)
```

## Using ForecasterDirect

```python
from skforecast.direct import ForecasterDirect

# Must specify `steps` at creation — trains one model per step
forecaster = ForecasterDirect(
    estimator=RandomForestRegressor(n_estimators=100, random_state=123),
    lags=24,
    steps=10,
    categorical_features='auto',  # Auto-detect and encode non-numeric exog columns
)
forecaster.fit(y=y_train, exog=exog_train)
predictions = forecaster.predict(exog=exog_test)
```

## Common Mistakes

1. **Missing frequency on index**: Always call `data.asfreq('h')` (or `'D'`, `'MS'`, etc.).
2. **NaN in data**: Forecasters reject NaN by default. Use `dropna_from_series=True` to drop incomplete rows, or keep `dropna_from_series=False` (default) with NaN-tolerant estimators (LightGBM, CatBoost, HistGradientBoosting, XGBoost hist). Alternatively, impute missing values first.
3. **Exog not covering forecast horizon**: The exogenous DataFrame for `predict()` must have rows for every future step.
4. **Random train/test split**: Time series must be split chronologically, never shuffled.
5. **Forgetting `store_in_sample_residuals=True`**: Required before calling `predict_interval()` with `method='bootstrapping'` on a standalone forecaster. During backtesting, residuals are computed automatically.
