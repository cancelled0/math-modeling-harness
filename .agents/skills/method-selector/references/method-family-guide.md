# Method-Family Routing Guide

Use this guide to form a shortlist, not as a menu that must be exhausted.

## Evaluation and ranking

- Credible baselines: equal-weight normalized score or an existing operational rule, when they complete the real task.
- Main families: entropy/TOPSIS, PCA-assisted evaluation, grey/fuzzy evaluation when their assumptions fit.
- Key risks: redundant indicators, unjustified directions or weights, weight dominance, concentrated scores, unstable top-k ranks.
- Route indicator construction and evidence-backed reduction through `feature-engineering`; use `statsmodels` for covariance or regression diagnostics when appropriate.

## Prediction

- Credible baselines: seasonal naive, last value, moving average, or simple regression selected to match the time structure.
- Main families: exponential smoothing, ARIMA/SARIMA, regression, tree boosting, small-data grey models.
- Key risks: leakage, invalid split, short series, nonstationarity, over-capacity, poor interval coverage.
- Route a chosen single-series family through `skforecast-recursive-direct`; use `statsmodels` for ACF/PACF or ARIMA diagnostics and `scikit-learn` for estimator pipelines.

## Optimization

- Credible baselines: current policy, a feasible greedy rule, or a relaxed exact formulation.
- Main families: LP/MILP, network flow, dynamic or nonlinear programming, justified metaheuristics.
- Key risks: missing constraints, infeasibility, meaningless objectives, nonimplementable solutions, excessive runtime.
- Route LP/MILP/QP formulation through `cuopt-numerical-optimization-formulation`; multi-objective evolutionary optimization through `pymoo`.

## Classification and clustering

- Credible baselines: rule-based or majority/stratified reference when meaningful.
- Main families: logistic/tree models, SVM, random forest, k-means or other clustering with validation.
- Key risks: label absence, class imbalance, arbitrary cluster count, instability, accuracy-only evaluation.
- Route reproducible pipelines through `scikit-learn`; use `shap` only after model validation for explanation, not for model approval.

## Mechanism and simulation

- Credible baselines: simplified algebraic or deterministic scenario model that preserves the core mechanism.
- Main families: differential/difference equations, compartment models, Monte Carlo, discrete-event or agent-based simulation.
- Key risks: unidentified parameters, unit errors, invalid boundary conditions, hidden distribution assumptions, too few replications.
- Route discrete-event simulation through `simpy`, Bayesian/hierarchical uncertainty through `pymc`, symbolic derivation through `sympy`, and unit propagation through `uncertainty-and-units`.

## Graph and routing

- Credible baselines: feasible direct rule or nearest-neighbor heuristic.
- Main families: shortest path, flow, matching, spanning tree, TSP/VRP formulations.
- Key risks: unrealistic edges or weights, omitted operational constraints, mathematically valid but unusable routes.
- Route graph construction and algorithms through `networkx`; spatial vector preprocessing through `geopandas` when geometry is load-bearing.

## Statistical inference and econometrics

- Credible baselines: descriptive comparison or a simple interpretable regression that answers the real question.
- Main families: hypothesis tests, OLS/GLM, mixed or panel models, time-series regression, or robust alternatives.
- Key risks: violated assumptions, endogeneity, multiple testing, collinearity, selective reporting.
- Route test design and effect-size reasoning through `statistical-analysis`, then use `statsmodels` for model fitting and diagnostics.

## No dedicated specialist

When no installed specialist matches the approved family, write an explicit method contract covering equations, inputs, constraints, reference policy, metrics, numerical risks, and fallback trigger. After G2.5, hand that contract to `model-code-analyzer` and the appropriate language generator. Do not invent a missing Skill dependency.
