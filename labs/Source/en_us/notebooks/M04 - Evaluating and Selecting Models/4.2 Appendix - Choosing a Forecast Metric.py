# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 4.2 Appendix — Choosing a Forecast Metric
# MAGIC
# MAGIC In 4.1 the "best model" for each series is simply the one with the lowest metric. So the metric is not a detail of the report: **it decides which model you deploy**. This appendix shows — interactively — how the five metrics MMF offers judge the same forecasts, and why the right one depends on how sparse and how spiky your series are.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Before you start: compute
# MAGIC
# MAGIC Sections A–C run no Spark job: any compute works, including **Serverless**, and the explorer runs entirely in your browser. Section D (optional) reads the workshop's reference results; run it on **Serverless**.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lesson you can:
# MAGIC - Describe what each of MMF's metrics (`smape`, `mape`, `mae`, `mse`, `rmse`) penalises, and which forecast it rewards.
# MAGIC - Recognise when a metric is misleading: zero-sales days, intermittent series, promotion spikes, series of very different sizes.
# MAGIC - Choose a metric for model selection, and check a winner's bias before trusting it.

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Metrics in MMF
# MAGIC
# MAGIC `run_forecast(..., metric="smape")` takes one of five metrics (default `smape`). For every series, model and backtest window, MMF scores the 28 forecast days against the actuals with sktime and writes **one row** to the evaluation table: the metric's value, plus the `forecast` and `actual` arrays. Only the chosen metric is computed — but the arrays let you compute any other afterwards (section D). Lesson 4.1 then averages each model's windows and keeps the lowest per series.
# MAGIC
# MAGIC For actual `y` and forecast `ŷ` on each day, averaged over the window's days:
# MAGIC
# MAGIC | `metric` | Per day | Rewards (best flat forecast) | Zero-sales days | Scale-free? |
# MAGIC |----------|---------|------------------------------|-----------------|-------------|
# MAGIC | `smape` (default) | 2·\|y − ŷ\| / (\|y\| + \|ŷ\|) | — (bounded by 2; misses below the actual cost more than misses above) | 0 if `ŷ` is exactly 0, else **2** — the maximum | Yes |
# MAGIC | `mape` | \|y − ŷ\| / \|y\| | Forecasts that are too low | Divides by ~0: about **10¹⁵** unless `ŷ` is exactly 0 | Yes |
# MAGIC | `mae` | \|y − ŷ\| | The **median** | Fine | No — in units |
# MAGIC | `mse` | (y − ŷ)² | The **mean** | Fine | No — in units² |
# MAGIC | `rmse` | √ of the window's MSE | The **mean** | Fine | No — in units |
# MAGIC
# MAGIC sktime replaces any denominator below machine epsilon (about 2.2·10⁻¹⁶) with epsilon, which is where MAPE's 10¹⁵ comes from. Common metrics MMF does not offer — **WAPE** (Σ\|y − ŷ\| / Σ\|y\|), **MASE**, **RMSSE** (the M5 competition used a weighted RMSSE) — can be computed from the stored arrays.

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Explore
# MAGIC
# MAGIC The explorer builds one daily series from four settings — share of zero-sales days, units on a selling day, day-to-day variability, promotion spikes — and backtests four simple forecasts on 3 windows of 28 days (`backtest_length=84`, `stride=28`):
# MAGIC - **Zero** — never sells anything;
# MAGIC - **Median (28 d)** and **Mean (28 d)** — a flat line at the median or mean of the last 28 days (MMF's intermittent-demand models, Croston and TSB, produce mean-like flat forecasts);
# MAGIC - **Seasonal Naive** — next week repeats last week.
# MAGIC
# MAGIC The table scores them with the five metrics, using sktime's formulas, highlights each metric's winner, and replays the settings on 100 alternative histories. The **bias** row compares each forecast's total with the actual total. The last panel shows the penalty each metric gives a single day.
# MAGIC
# MAGIC **Try this:**
# MAGIC 1. Click **Typical M5 item** (about two-thirds of days have zero sales, as in most M5 series). Which forecast do sMAPE, MAPE and MAE select? Read its bias.
# MAGIC 2. Click **Slow mover (a few zero days)**. sMAPE now behaves — what does MAPE select, and why?
# MAGIC 3. Click **Promotions**, and compare MAE's and RMSE's winners and biases.
# MAGIC 4. Click **Fast mover** and **New random history** a few times: does the metric matter here? Look at the last column.
# MAGIC 5. In panel 3, compare the penalties for a forecast half too low and half too high at an actual of 10, then move the actual to 0.

# COMMAND ----------

# MAGIC %run ../Includes/_metric_explorer

# COMMAND ----------

displayHTML(METRIC_EXPLORER_HTML)

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. What you should see
# MAGIC
# MAGIC <details>
# MAGIC <summary><b>Show the answers</b></summary>
# MAGIC
# MAGIC 1. **Three metrics select a forecast that sells nothing.** On the typical M5 item, sMAPE, MAPE and MAE all crown **Zero** in almost every history, with a bias of −100%: deployed, it would never stock the item. sMAPE scores every miss on a zero day with its maximum 2, however small the forecast, and an exact zero as perfect; MAE rewards the median, which is 0 once more than half the days are zero. MSE and RMSE select the **Mean** — the only forecast that gets the total roughly right.
# MAGIC 2. **One zero day is enough to break MAPE.** With only about 5–10% zero days, every non-zero forecast gets a MAPE around 10¹⁴–10¹⁵, so MAPE selects Zero. sMAPE, MAE and RMSE pick sensible forecasts here.
# MAGIC 3. **Spikes split the metrics.** On the promotions series, sMAPE and MAE select the **Median**, which ignores promotion days (bias about −20%); RMSE, dominated by the large misses on those days, selects the **Mean** (bias close to 0). Which one is right is a business question: do promotion days have to be stocked? Better still, forecast promotions explicitly with exogenous variables.
# MAGIC 4. **Sometimes the metric doesn't matter.** On the fast mover all metrics usually agree, but the stability column is low: the candidates are close, and a different history would crown another one. That is a backtest-length problem (3.1), not a metric problem.
# MAGIC 5. **Percentage metrics are asymmetric.** At an actual of 10, forecasting 5 costs sMAPE 0.67 and forecasting 15 costs 0.40: sMAPE punishes under-forecasts more. MAPE charges both 0.5, but an under-forecast can never cost more than 1 while an over-forecast is unbounded, so MAPE favours forecasts that are too low. At an actual of 0, sMAPE jumps from 0 to 2 and MAPE to about 10¹⁵ for any forecast above 0, while MAE and MSE grow smoothly.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. On the workshop's results (optional)
# MAGIC
# MAGIC The reference results in `mmf.m5_reference` were scored with sMAPE, but each row also holds the 28 `forecast` and `actual` values, so you can re-score every window with other metrics and see whether the winner per series changes. The first column checks that the recomputed sMAPE matches MMF's.

# COMMAND ----------

dbutils.widgets.text("evaluation_table", "mmf.m5_reference.m5_evaluation_output")
evaluation_table = dbutils.widgets.get("evaluation_table")

try:
    has_results = spark.catalog.tableExists(evaluation_table)
except Exception:
    has_results = False
if not has_results:
    print(f"{evaluation_table} not found — section D needs the workshop's reference results; skip it.")

# COMMAND ----------

if has_results:
    spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW rescored AS
    WITH windows AS (
        SELECT
            unique_id, model, backtest_window_start_date,
            ANY_VALUE(metric_value) FILTER (WHERE metric_name = 'smape') AS mmf_smape,
            ANY_VALUE(actual) AS actual,
            ANY_VALUE(forecast) AS forecast
        FROM {evaluation_table}
        GROUP BY ALL
    ),
    per_window AS (
        SELECT
            unique_id, model, mmf_smape,
            -- sktime: denominators below machine epsilon are replaced by epsilon
            AGGREGATE(ZIP_WITH(actual, forecast, (a, f) -> 2 * ABS(a - f) / GREATEST(ABS(a) + ABS(f), 2.220446049250313e-16)), 0D, (s, x) -> s + x) / SIZE(actual) AS smape,
            AGGREGATE(ZIP_WITH(actual, forecast, (a, f) -> ABS(a - f)), 0D, (s, x) -> s + x) / SIZE(actual) AS mae,
            SQRT(AGGREGATE(ZIP_WITH(actual, forecast, (a, f) -> (a - f) * (a - f)), 0D, (s, x) -> s + x) / SIZE(actual)) AS rmse,
            AGGREGATE(actual, 0D, (s, x) -> s + x) AS actual_total,
            AGGREGATE(forecast, 0D, (s, x) -> s + x) AS forecast_total,
            SIZE(FILTER(actual, a -> a = 0)) / SIZE(actual) AS zero_share
        FROM windows
    )
    SELECT
        unique_id, model,
        AVG(smape) AS smape, AVG(mae) AS mae, AVG(rmse) AS rmse,
        SUM(forecast_total) / NULLIF(SUM(actual_total), 0) - 1 AS bias,
        AVG(zero_share) AS zero_share,
        MAX(ABS(smape - mmf_smape)) AS smape_check
    FROM per_window
    GROUP BY ALL
    """)
    display(spark.sql("""
        SELECT COUNT(DISTINCT unique_id) AS series, COUNT(DISTINCT model) AS models,
               MAX(smape_check) AS max_diff_vs_mmf_smape
        FROM rescored
    """))

# COMMAND ----------

# MAGIC %md
# MAGIC Pick the winner per series under each metric (lowest average over windows; ties to the model name, unlike 4.1's simpler-model rule), then compare by how sparse the series are:

# COMMAND ----------

if has_results:
    spark.sql("""
    CREATE OR REPLACE TEMP VIEW winners AS
    SELECT unique_id, ANY_VALUE(zero_share) AS zero_share,
        MIN_BY(model, STRUCT(smape, model)) AS by_smape, MIN_BY(bias, STRUCT(smape, model)) AS bias_smape,
        MIN_BY(model, STRUCT(mae, model))   AS by_mae,   MIN_BY(bias, STRUCT(mae, model))   AS bias_mae,
        MIN_BY(model, STRUCT(rmse, model))  AS by_rmse,  MIN_BY(bias, STRUCT(rmse, model))  AS bias_rmse
    FROM rescored
    GROUP BY unique_id
    """)
    display(spark.sql("""
        SELECT
            CASE WHEN zero_share >= 0.5 THEN '1. half or more zero days'
                 WHEN zero_share >= 0.1 THEN '2. 10-50% zero days'
                 ELSE '3. under 10% zero days' END AS series_profile,
            COUNT(*) AS series,
            ROUND(AVG(CAST(by_smape <> by_rmse AS INT)), 2) AS share_winner_differs_smape_vs_rmse,
            ROUND(AVG(CAST(by_smape <> by_mae AS INT)), 2) AS share_winner_differs_smape_vs_mae,
            ROUND(AVG(bias_smape), 2) AS avg_bias_smape_winner,
            ROUND(AVG(bias_rmse), 2) AS avg_bias_rmse_winner
        FROM winners
        GROUP BY ALL ORDER BY series_profile
    """))

# COMMAND ----------

# MAGIC %md
# MAGIC Wins per model under each metric:

# COMMAND ----------

if has_results:
    display(spark.sql("""
        SELECT model,
               COUNT_IF(by_smape = model) AS wins_smape,
               COUNT_IF(by_mae = model) AS wins_mae,
               COUNT_IF(by_rmse = model) AS wins_rmse
        FROM winners CROSS JOIN (SELECT DISTINCT model FROM rescored)
        GROUP BY model ORDER BY wins_smape DESC
    """))

# COMMAND ----------

# MAGIC %md
# MAGIC Look for: how often the winner changes on the sparse series, the bias of the sMAPE winners there (negative means they under-forecast), and which models gain wins under RMSE.

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Choosing a metric in practice
# MAGIC
# MAGIC | Your series | Use for model selection | Avoid |
# MAGIC |-------------|------------------------|-------|
# MAGIC | No zero days, decent volume | `smape` (scale-free, so it averages across series), or `mae` | — |
# MAGIC | Some zero days (slow movers) | `mae` or `rmse` | `mape` — a single zero day breaks it |
# MAGIC | Intermittent (most days zero — most M5 series) | `rmse` (rewards forecasts with the right total), or MASE / RMSSE computed from the arrays | `mape`, and `smape` / `mae`, which reward forecasting zero |
# MAGIC | Promotions or spikes you must stock for | `rmse`, or model the promotions with exogenous variables | `mae`, `smape` if spikes matter |
# MAGIC
# MAGIC - **Select per series, report across series.** Within one series every model is scored on the same actuals, so a scale-dependent metric (MAE, RMSE) is fine for picking its winner. Across series — 4.1's leaderboard averages, a single accuracy figure for management — use a scale-free one such as **WAPE** (Σ\|error\| / Σ actual), or big series dominate. Per series, WAPE picks the same winner as MAE.
# MAGIC - **Always check bias next to the winner.** A low error with a large negative bias means empty shelves; a large positive one, overstock.
# MAGIC - **Match the business cost.** If a missed sale costs much more than an unsold unit (or the reverse), a symmetric metric picks the wrong trade-off; that calls for quantile (probabilistic) forecasts, which are beyond this workshop.
# MAGIC - **Changing the metric means re-running.** `run_forecast` stores only the chosen metric. Re-run with `metric="rmse"` (e.g. ask Genie Code in 3.3), or re-score the stored arrays as in section D.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC The metric decides which model wins. Percentage metrics are scale-free but break on zero-sales days — MAPE completely, sMAPE by rewarding zero forecasts — and that matters for M5, where most series are intermittent. MAE rewards the median and RMSE the mean, so on sparse or spiky series they select different models with different biases. Choose the metric from your series' profile and your business costs, and always read a winner's bias. **Back to:** *4.1 Lab — Best Model per Series*, whose `metric` widget selects which stored metric to rank by.
