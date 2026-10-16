# Lab 5 — Evaluate and Select Best Models

## Purpose

Post-process the forecasting results: select the best model per series, build a summary leaderboard, and understand where each model class excels. This is where you answer the business question: *"Which model should we deploy for each product?"*

## What Databricks/MMF brings

- **Automatic model comparison** — MMF stores all backtest results in a single evaluation table, so comparing models is a SQL query, not a data engineering project.
- **Foundation model reference results** — even without GPU access, pre-computed Chronos-Bolt-Small results are automatically merged into your evaluation table, so you see all model classes side by side.
- **Best-model selection** — picks the winner per series based on average metric across backtest windows, with tie-breaking that favours simpler models (cheaper to deploy).
- **Genie Code exploration** — ask natural-language questions of the results: *"Which category has the worst SMAPE?"*, *"Which model wins most often for intermittent series?"*

## Hints

- The evaluation table uses long format: `metric_name` + `metric_value` (not a column per metric). Filter on `metric_name = 'smape'`.
- Tie-breaking order: StatsForecast > MLForecast > NeuralForecast > Foundation. This means a simple model wins when it ties with a complex one — a good production default.
- Look at the **worst-performing series** (high SMAPE) — these are often intermittent items where all models struggle. In production, you might handle them differently (e.g., Croston for intermittent, LightGBM for smooth).
- Try changing the metric from `smape` to `mase` or `wape` and re-running — the best model per series can change significantly.
- Ask Genie Code: *"Show me series where the foundation model beats all statistical models"* to find where deep learning adds value.
