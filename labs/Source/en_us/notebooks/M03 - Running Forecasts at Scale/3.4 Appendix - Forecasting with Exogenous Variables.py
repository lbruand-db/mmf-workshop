# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 3.4 Appendix — Forecasting with Exogenous Variables
# MAGIC
# MAGIC So far every model has forecast sales from past sales alone. But retail demand also follows things you **know in advance**: food-stamp (SNAP) days, holidays and events, planned price changes. This appendix feeds those to MMF as **exogenous variables** (regressors), runs the same LightGBM model with and without them, and measures what they add — on the backtest and on 28 days the models have never seen.
# MAGIC
# MAGIC Optional, about 20 minutes including two forecast runs of a few minutes each. It needs nothing from earlier lessons.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Before you start: compute
# MAGIC
# MAGIC Select **Serverless** in the compute drop-down at the top right of the notebook before running any cell.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lesson you can:
# MAGIC - Tell static, dynamic future and dynamic historical regressors apart, and say which MMF models use each.
# MAGIC - Build the two tables MMF needs for future regressors: a training table and a **scoring table** with the future values.
# MAGIC - Run `run_forecast` with `dynamic_future_numerical`, and judge whether the regressors helped.

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Exogenous variables in MMF
# MAGIC
# MAGIC | Kind | Known… | M5 examples | `run_forecast` parameter | Used by |
# MAGIC |------|--------|-------------|--------------------------|---------|
# MAGIC | **Static** | once per series | store, department, category | `static_features` | Global and foundation models |
# MAGIC | **Dynamic future** | for the past **and** the forecast horizon | SNAP days, calendar events, planned prices | `dynamic_future_numerical`, `dynamic_future_categorical` | Global ML (LightGBM), some local models, foundation models |
# MAGIC | **Dynamic historical** | only up to today | e.g. observed weather, competitor prices | `dynamic_historical_numerical`, `dynamic_historical_categorical` | Global deep-learning and foundation models |
# MAGIC
# MAGIC **Dynamic future regressors need their future values.** You pass them in a separate `scoring_data` table: one row per series and future day, with the regressor columns and **no target**. MMF unions it with the training data when it scores, and uses each backtest window's actual regressor values when it evaluates.
# MAGIC
# MAGIC Which models use them:
# MAGIC - **LightGBM** (`MLForecastLGBM`) uses them as extra features — the setup the MMF skill recommends for future regressors, and the one this appendix runs.
# MAGIC - Among **local** models, only `StatsForecastAutoArima` (and other ARIMA-type models) use them. The workshop's Seasonal Naive, AutoETS, Croston and TSB ignore them — passing regressors to them does no harm.
# MAGIC - Regressor values must be **numbers** (encode categories as integers first) and must have **no NULLs**: MMF's data-quality check drops series with missing regressor values.

# COMMAND ----------

# MAGIC %md
# MAGIC `mmf_sa` is installed from the pinned wheel staged by `setup/workspace_setup`.

# COMMAND ----------

# MAGIC %pip install -r /Volumes/mmf/m5/assets/wheels/requirements-cpu.txt --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import logging
import uuid
from datetime import timedelta

logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom setup

# COMMAND ----------

# MAGIC %run ../Includes/Classroom-Setup-3.4

# COMMAND ----------

dbutils.widgets.text("run_id", "")
run_id = dbutils.widgets.get("run_id") or str(uuid.uuid4())

HORIZON = 28
FEATURES = ["snap", "is_event", "relative_price"]
source_table = f"{source}.daily_train_100"
print(f"Source: {source_table}   Run ID: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. The regressors in M5
# MAGIC
# MAGIC The shared table already carries M5's calendar and price columns next to the sales: `snap_CA` / `snap_TX` / `snap_WI` (1 on SNAP days in that state), `event_name_1` (`'nan'` when there is no event) and the weekly `sell_price`. All three are known ahead of time — the SNAP calendar and holidays are published, and prices are planned.

# COMMAND ----------

display(spark.sql(f"""
    SELECT unique_id, ds, y, snap_CA, snap_TX, snap_WI, event_name_1, event_type_1, sell_price
    FROM {source_table}
    WHERE event_name_1 <> 'nan'
    ORDER BY ds DESC LIMIT 10
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC We turn them into three numeric regressors, and hold out the last 28 days as a "future" the models don't see:
# MAGIC
# MAGIC | Regressor | Definition |
# MAGIC |-----------|------------|
# MAGIC | `snap` | 1 on a SNAP day in the series' own state (taken from its `unique_id`, e.g. `…_CA_1`) |
# MAGIC | `is_event` | 1 on a calendar event day (sporting, cultural, national or religious) |
# MAGIC | `relative_price` | Price relative to the series' average price over the training period — below 1 means a discount |
# MAGIC
# MAGIC - `m5_exog_train` — history with `y` and the regressors, up to the cut-off.
# MAGIC - `m5_exog_future` — the 28 days after the cut-off: `unique_id`, `ds` and the regressors only. This is the **scoring table**.

# COMMAND ----------

last_ds = spark.sql(f"SELECT MAX(ds) AS d FROM {source_table}").first()["d"]
cutoff = last_ds - timedelta(days=HORIZON)
print(f"Training data up to {cutoff:%Y-%m-%d}; held-out future: the {HORIZON} days to {last_ds:%Y-%m-%d}")

spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW exog_all AS
    SELECT
        unique_id, ds, y,
        CAST(CASE element_at(split(unique_id, '_'), -2)
                 WHEN 'CA' THEN snap_CA WHEN 'TX' THEN snap_TX ELSE snap_WI END AS DOUBLE) AS snap,
        CAST(event_name_1 <> 'nan' AS DOUBLE) AS is_event,
        sell_price / AVG(CASE WHEN ds <= '{cutoff}' THEN sell_price END) OVER (PARTITION BY unique_id) AS relative_price
    FROM {source_table}
""")
spark.sql(f"CREATE OR REPLACE TABLE {out}.m5_exog_train AS SELECT * FROM exog_all WHERE ds <= '{cutoff}'")
spark.sql(f"CREATE OR REPLACE TABLE {out}.m5_exog_future AS SELECT unique_id, ds, {', '.join(FEATURES)} FROM exog_all WHERE ds > '{cutoff}'")

display(spark.sql(f"""
    SELECT 'm5_exog_train' AS table, COUNT(DISTINCT unique_id) AS series, COUNT(*) AS rows, MIN(ds) AS first_ds, MAX(ds) AS last_ds,
           COUNT_IF(relative_price IS NULL) AS null_regressors FROM {out}.m5_exog_train
    UNION ALL
    SELECT 'm5_exog_future', COUNT(DISTINCT unique_id), COUNT(*), MIN(ds), MAX(ds),
           COUNT_IF(relative_price IS NULL) FROM {out}.m5_exog_future
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC Do the regressors move sales at all? Average daily sales on SNAP, event and discount days, relative to the other days (1.00 = no effect), by department category:

# COMMAND ----------

display(spark.sql(f"""
    SELECT
        element_at(split(unique_id, '_'), 1) AS category,
        COUNT(DISTINCT unique_id) AS series,
        ROUND(AVG(y) FILTER (WHERE snap = 1) / AVG(y) FILTER (WHERE snap = 0), 2) AS snap_lift,
        ROUND(AVG(y) FILTER (WHERE is_event = 1) / AVG(y) FILTER (WHERE is_event = 0), 2) AS event_lift,
        ROUND(AVG(y) FILTER (WHERE relative_price < 0.95) / AVG(y) FILTER (WHERE relative_price >= 0.95), 2) AS discount_lift
    FROM {out}.m5_exog_train
    GROUP BY 1 ORDER BY 1
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC Expect **discount** days to show the biggest lift in every category (but they are rare), **SNAP** days to lift FOODS more than the other categories (SNAP benefits buy food), and **event** days to sit at or slightly below normal — many events are holidays when people shop less. A regressor can only help where it moves the target, and a regressor that *lowers* sales is just as useful as one that raises them.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Run LightGBM with and without regressors
# MAGIC
# MAGIC Both runs use the same model and settings as the workshop (28-day horizon, `backtest_length=56`, `stride=28`) and write to the same tables; `use_case` tells them apart. The only differences in the second run: `scoring_data` points to the future table, and `dynamic_future_numerical` lists the regressors.

# COMMAND ----------

from mmf_sa import run_forecast

common = dict(
    spark=spark,
    train_data=f"{out}.m5_exog_train",
    scoring_output=f"{out}.m5_exog_scoring_output",
    evaluation_output=f"{out}.m5_exog_evaluation_output",
    model_output=out,
    group_id="unique_id",
    date_col="ds",
    target="y",
    freq="D",
    prediction_length=HORIZON,
    backtest_length=56,
    stride=28,
    metric="smape",
    train_predict_ratio=1,
    data_quality_check=True,
    resample=False,
    active_models=["MLForecastLGBM"],
    experiment_path=f"/Users/{user_email}/mmf_m5_workshop",
    run_id=run_id,
    accelerator="cpu",
)

# Without regressors: scoring_data = train_data, so MMF forecasts the 28 days after the cut-off from sales alone.
run_forecast(**common, scoring_data=f"{out}.m5_exog_train", use_case_name="m5_no_exog")
print("Run without regressors complete.")

# COMMAND ----------

# With regressors: the future table supplies snap / is_event / relative_price for the 28 forecast days.
run_forecast(
    **common,
    scoring_data=f"{out}.m5_exog_future",
    dynamic_future_numerical=FEATURES,
    use_case_name="m5_exog",
)
print("Run with regressors complete.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Did the regressors help?
# MAGIC
# MAGIC Two views. The **backtest** (MMF's evaluation table) is what model selection would see. The **held-out 28 days** compare each run's forecast with what really sold — the honest test. Following *4.2 Appendix — Choosing a Forecast Metric*, read sMAPE together with scale-aware metrics and the bias: many M5 series are mostly zeros.

# COMMAND ----------

spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW holdout AS
    WITH fc AS (
        SELECT s.use_case, s.unique_id, z.ds, z.y AS forecast
        FROM {out}.m5_exog_scoring_output s
        LATERAL VIEW explode(arrays_zip(s.ds, s.y)) t AS z
        WHERE s.run_id = '{run_id}'
    )
    SELECT fc.use_case, fc.unique_id, fc.ds, fc.forecast, a.y AS actual
    FROM fc JOIN {source_table} a ON a.unique_id = fc.unique_id AND a.ds = fc.ds
""")

display(spark.sql(f"""
    WITH backtest AS (
        SELECT use_case, ROUND(AVG(metric_value), 3) AS backtest_smape
        FROM {out}.m5_exog_evaluation_output
        WHERE run_id = '{run_id}'
        GROUP BY use_case
    ),
    future AS (
        SELECT use_case,
            COUNT(DISTINCT unique_id) AS series,
            ROUND(AVG(2 * ABS(actual - forecast) / GREATEST(ABS(actual) + ABS(forecast), 2.220446049250313e-16)), 3) AS holdout_smape,
            ROUND(AVG(ABS(actual - forecast)), 3) AS holdout_mae,
            ROUND(SQRT(AVG(POW(actual - forecast, 2))), 3) AS holdout_rmse,
            ROUND(SUM(ABS(actual - forecast)) / SUM(actual), 3) AS holdout_wape,
            ROUND(SUM(forecast) / SUM(actual) - 1, 3) AS holdout_bias
        FROM holdout GROUP BY use_case
    )
    SELECT * FROM backtest JOIN future USING (use_case) ORDER BY use_case DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC Where do they help? WAPE over the held-out 28 days by category, and the share of series whose error went down with the regressors:

# COMMAND ----------

display(spark.sql("""
    WITH per_series AS (
        SELECT unique_id, element_at(split(unique_id, '_'), 1) AS category,
            SUM(ABS(actual - forecast)) FILTER (WHERE use_case = 'm5_no_exog') AS err_no_exog,
            SUM(ABS(actual - forecast)) FILTER (WHERE use_case = 'm5_exog') AS err_exog,
            SUM(actual) FILTER (WHERE use_case = 'm5_exog') AS actual_total
        FROM holdout GROUP BY ALL
    )
    SELECT category, COUNT(*) AS series,
        ROUND(SUM(err_no_exog) / SUM(actual_total), 3) AS wape_no_exog,
        ROUND(SUM(err_exog) / SUM(actual_total), 3) AS wape_exog,
        ROUND(AVG(CAST(err_exog < err_no_exog AS INT)), 2) AS share_series_improved
    FROM per_series
    GROUP BY category ORDER BY category
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC One series up close — the FOODS series with the most sales in the held-out period, with SNAP and event days marked:

# COMMAND ----------

import matplotlib.pyplot as plt

top = spark.sql("""
    SELECT unique_id FROM holdout
    WHERE use_case = 'm5_exog' AND unique_id LIKE 'FOODS%'
    GROUP BY unique_id ORDER BY SUM(actual) DESC LIMIT 1
""").first()["unique_id"]

pdf = spark.sql(f"""
    SELECT h.ds, h.use_case, h.forecast, h.actual, f.snap, f.is_event
    FROM holdout h JOIN {out}.m5_exog_future f USING (unique_id, ds)
    WHERE h.unique_id = '{top}' ORDER BY h.ds
""").toPandas()
wide = pdf.pivot_table(index="ds", columns="use_case", values="forecast")
days = pdf.drop_duplicates("ds").set_index("ds")

fig, ax = plt.subplots(figsize=(11, 3.8))
for d in days.index[days.snap == 1]:
    ax.axvspan(d - timedelta(hours=12), d + timedelta(hours=12), color="#dcfce7", lw=0)
for d in days.index[days.is_event == 1]:
    ax.axvline(d, color="#d97706", ls=":", lw=1.5)
ax.plot(days.index, days.actual, color="#6b7280", lw=1.5, label="actual")
ax.plot(wide.index, wide["m5_no_exog"], color="#2563eb", lw=1.8, label="LightGBM, sales only")
ax.plot(wide.index, wide["m5_exog"], color="#ea580c", lw=1.8, label="LightGBM + regressors")
ax.set_title(f"{top}: held-out 28 days (green: SNAP days, dotted: events)")
ax.legend(loc="upper left", frameon=False)
plt.tight_layout()
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC <details>
# MAGIC <summary><b>How to read these results</b></summary>
# MAGIC
# MAGIC - **Expect a modest, uneven gain** — typically a few percent better WAPE and RMSE, with more than half of the series improving.
# MAGIC - **Why only modest?** LightGBM already sees the weekday and recent sales through its lags; the regressors add what lags can't anticipate — the SNAP calendar (which shifts each month), event days and price changes. The gain is spread thinly across categories; on the many near-zero series there is little to explain. (The results cover 99 series: MMF's data-quality check drops one series that fails its checks, with or without regressors.)
# MAGIC - **The backtest and the held-out period can disagree.** Both are only 28–56 days, on 100 series (see *3.1*): treat a difference of a few hundredths as noise, and look at the category and per-series views before concluding.
# MAGIC - **sMAPE can hide a real gain** on intermittent series (*4.2*): compare WAPE, RMSE and the bias as well.
# MAGIC - **Regressors are only as good as their future values.** Here the future values are the real ones. In production you would use the planned SNAP calendar, the event calendar and the planned prices — and a wrong price plan becomes a wrong forecast.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. With Genie Code
# MAGIC
# MAGIC The MMF skill handles regressors in Skill 1 and Skill 4. To rebuild this run with Genie Code, start a new conversation and use these answers at its gates:
# MAGIC
# MAGIC | Gate | Answer |
# MAGIC |------|--------|
# MAGIC | Source table | `{out}.m5_exog_train` (printed by the Classroom setup) — it already has the regressors |
# MAGIC | Step 5a — exogenous regressors? | **Yes** → **Dynamic future**: `snap`, `is_event`, `relative_price` (all numerical) |
# MAGIC | Step 5b — where do future values come from? | **Separate table**: `{out}.m5_exog_future` |
# MAGIC | Models | **LightGBM** (global ML) — the skill's validated path for future regressors |
# MAGIC
# MAGIC The skill checks that the scoring table covers every series and future day, and asks before handling any NULLs.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check your work

# COMMAND ----------

# MAGIC %run ../Includes/_checks

# COMMAND ----------

checks = []
for table in ["m5_exog_train", "m5_exog_future"]:
    try:
        n = spark.table(f"{out}.{table}").count()
        checks.append((f"{table} exists", n > 0, f"{n} rows"))
    except Exception as e:
        checks.append((f"{table} exists", False, str(e)))

try:
    cases = {r["use_case"] for r in spark.table(f"{out}.m5_exog_scoring_output").select("use_case").distinct().collect()}
    checks.append(("Forecasts with and without regressors", {"m5_exog", "m5_no_exog"} <= cases, f"{sorted(cases)}"))
except Exception as e:
    checks.append(("Forecasts with and without regressors", False, str(e)))

finish("3.4 Appendix", checks)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC You added known-in-advance information — SNAP days, events, relative prices — to an MMF forecast: a training table with the regressors, a scoring table with their future values, and `dynamic_future_numerical` in `run_forecast`. You measured the effect on the backtest and on a held-out month, by category. The same pattern works for any regressor you can provide for the forecast horizon: promotions, store openings, planned marketing.
