# Databricks notebook source
# MAGIC %md
# MAGIC # 3.3 Lab — Provision and Execute with Genie Code
# MAGIC
# MAGIC Run the MMF forecasting pipeline with **MMF Skills 3 and 4**: local statistical models and global ML, in parallel, with backtesting and MLflow tracking.
# MAGIC
# MAGIC **What Databricks brings**
# MAGIC - **`run_forecast()`** handles train/test splits, backtesting, scoring and metrics for every model class — no loop over series.
# MAGIC - **Parallel execution**: MMF spreads model fits across Spark.
# MAGIC - **Model diversity**: statistical models and LightGBM run through the same interface and are compared on equal footing.
# MAGIC - **MLflow tracking**: every run is logged with parameters, metrics and artifacts.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom setup

# COMMAND ----------

# MAGIC %run ../Includes/Classroom-Setup-3.3

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Provision and run the forecast
# MAGIC
# MAGIC 1. In Genie Code, type `/provision-forecasting-resources`, then `/execute-mmf-forecast`.
# MAGIC 2. Choose the **CPU models** only: Seasonal Naive, AutoETS, AutoTheta, Croston Optimized, TSB, and LightGBM. GPUs aren't available in this lab — foundation model results are provided in 4.1.
# MAGIC 3. Pick the **smallest CPU** compute option.
# MAGIC 4. Accept a 28-day horizon (`prediction_length=28`), `backtest_length=90`, `stride=7`, metric sMAPE.
# MAGIC 5. The outputs are `m5_evaluation_output` and `m5_scoring_output` in your schema.

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. While the jobs run
# MAGIC
# MAGIC The run takes about 10 minutes. Open **Experiments** in the left menu and explore the MLflow runs: parameters, metrics, and per-series results. If a model fails for one series, MMF logs it and carries on.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Short on time?
# MAGIC
# MAGIC Run the next cell to copy the reference forecast results into your schema in seconds. They were produced by *3.2 Demo — MMF with mmf_sa* (5 local models + LightGBM, 100 series, `backtest_length=90`, `stride=7`) when the workspace was set up.

# COMMAND ----------

copied = {t: copy_table(f"{reference}.{t}", t) for t in ["m5_evaluation_output", "m5_scoring_output"]}
for t, n in copied.items():
    print(f"Copied {reference}.{t} -> {out}.{t} ({n} rows)")

models = sorted(r["model"] for r in spark.table(f"{out}.m5_evaluation_output").select("model").distinct().collect())
print(f"Models evaluated: {models}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check your work

# COMMAND ----------

# MAGIC %run ../Includes/_checks

# COMMAND ----------

checks = []

eval_table = f"{out}.m5_evaluation_output"
try:
    eval_df = spark.table(eval_table)
    eval_count = eval_df.count()
    checks.append(("Evaluation table exists", True, f"{eval_count} rows"))

    models = [r["model"] for r in eval_df.select("model").distinct().collect()]
    checks.append(("At least 2 models", len(models) >= 2, f"{sorted(models)}"))
except Exception as e:
    checks.append(("Evaluation table exists", False, str(e)))

scoring_table = f"{out}.m5_scoring_output"
try:
    scoring_count = spark.table(scoring_table).count()
    checks.append(("Scoring table exists", True, f"{scoring_count} rows"))
except Exception as e:
    checks.append(("Scoring table exists", False, str(e)))

finish("3.3", checks)
