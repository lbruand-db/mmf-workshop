# Lab 4 — Execute Forecast Models

## Purpose

Run the MMF forecasting pipeline across three model classes — local statistical models, global ML, and (optionally) foundation models. This is the core of the workshop: you see how MMF parallelises thousands of individual model fits across a Spark cluster with a single function call.

## What Databricks/MMF brings

- **`run_forecast()` API** — one function call that handles train/test splits, backtesting, scoring, and metric computation for any model class. No boilerplate loop over series.
- **Parallel execution** — MMF distributes model fits across Spark workers. 100 series × 5 models runs in ~5 minutes on serverless CPU.
- **Model diversity** — statistical models (SeasonalNaive, AutoETS, AutoTheta, CrostonOptimized, TSB), ML (LightGBM), and foundation models (Chronos) all run through the same interface. You compare them on equal footing.
- **MLflow tracking** — every run is logged as an MLflow experiment with metrics, parameters, and model artifacts.

## Hints

- Short on time? `catchup.py` copies the reference results into your schema in seconds.
- `run_cpu.py` is the reference solution: it runs 5 local + 1 global ML model on 100 series (~5–10 min) without the agent. Set `n_series=1000` to try a bigger run.
- Foundation models are in `run_foundation.py`, which needs a GPU. Pre-computed foundation results are merged in Lab 5.
- Key parameters to experiment with:
  - `backtest_length=90` — how many days of history to use for evaluation
  - `stride=7` — how often to slide the evaluation window
  - `prediction_length=28` — forecast horizon (28 days = 4 weeks)
- If a model fails for a specific series, MMF logs it and continues — check MLflow for per-series errors.
- Ask Genie Code: *"Run the local statistical models on 100 series"* to kick off Skill 4.
