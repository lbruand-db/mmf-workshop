# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 3.2 Demo — MMF with mmf_sa
# MAGIC
# MAGIC Runs the workshop model set on serverless CPU:
# MAGIC - **Local**: SeasonalNaive, AutoETS, AutoTheta, CrostonOptimized, TSB
# MAGIC - **Global ML**: LightGBM (MLForecast)
# MAGIC
# MAGIC Foundation models need a GPU and are not part of this demo; their results are
# MAGIC pre-computed and merged in 4.1.
# MAGIC
# MAGIC This is the forecast the agent builds in 3.3, written directly against
# MAGIC `mmf_sa` (~5–10 min on 100 series). It is also the **reference solution**:
# MAGIC `setup/workspace_setup` runs it once into `mmf.m5_reference`, which 3.3 and
# MAGIC 4.1 copy from when you skip ahead.

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
# MAGIC - Call `run_forecast` for local statistical models and a global ML model.
# MAGIC - Explain `prediction_length`, `backtest_length` and `stride`.
# MAGIC - Find the results in the evaluation and scoring tables, and in MLflow.

# COMMAND ----------

# MAGIC %md
# MAGIC `mmf_sa` is installed from the pinned wheel staged by `setup/workspace_setup`
# MAGIC (no download from GitHub).

# COMMAND ----------

# MAGIC %pip install -r /Volumes/mmf/m5/assets/wheels/requirements-cpu.txt --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid
import logging

logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom setup

# COMMAND ----------

# MAGIC %run ../Includes/Classroom-Setup-3.2

# COMMAND ----------

dbutils.widgets.text("n_series", "100")
dbutils.widgets.text("run_id", "")

n_series = dbutils.widgets.get("n_series")
run_id = dbutils.widgets.get("run_id") or str(uuid.uuid4())

train_table = f"{source}.daily_train_{n_series}"
print(f"Train data: {train_table}")
print(f"Run ID: {run_id}")


# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify training data exists

# COMMAND ----------

row_count = spark.table(train_table).count()
series_count = spark.table(train_table).select("unique_id").distinct().count()
print(f"Training data: {series_count} series, {row_count} rows")
assert row_count > 0, f"Training table {train_table} is empty"

# COMMAND ----------

# MAGIC %md
# MAGIC ### Run local statistical models

# COMMAND ----------

from mmf_sa import run_forecast

local_models = [
    "StatsForecastBaselineSeasonalNaive",
    "StatsForecastAutoETS",
    "StatsForecastAutoTheta",
    "StatsForecastCrostonOptimized",
    "StatsForecastTSB",
]

run_forecast(
    spark=spark,
    train_data=train_table,
    scoring_data=train_table,
    scoring_output=f"{out}.m5_scoring_output",
    evaluation_output=f"{out}.m5_evaluation_output",
    group_id="unique_id",
    date_col="ds",
    target="y",
    freq="D",
    prediction_length=28,
    backtest_length=90,
    stride=7,
    metric="smape",
    train_predict_ratio=1,
    data_quality_check=True,
    resample=False,
    active_models=local_models,
    experiment_path=f"/Users/{user_email}/mmf_m5_workshop",
    use_case_name="m5",
    run_id=run_id,
)

print("Local models complete.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Run global ML model (LightGBM)

# COMMAND ----------

global_ml_models = [
    "MLForecastLGBM",
]

run_forecast(
    spark=spark,
    train_data=train_table,
    evaluation_output=f"{out}.m5_evaluation_output",
    model_output=out,
    group_id="unique_id",
    date_col="ds",
    target="y",
    freq="D",
    prediction_length=28,
    backtest_length=90,
    stride=7,
    metric="smape",
    train_predict_ratio=1,
    data_quality_check=True,
    resample=False,
    active_models=global_ml_models,
    experiment_path=f"/Users/{user_email}/mmf_m5_workshop",
    use_case_name="m5",
    run_id=run_id,
    accelerator="cpu",
)

print("Global ML models complete.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify outputs

# COMMAND ----------

eval_count = spark.table(f"{out}.m5_evaluation_output").count()
eval_models = (
    spark.table(f"{out}.m5_evaluation_output")
    .select("model").distinct().collect()
)
model_names = sorted([r["model"] for r in eval_models])

print(f"Evaluation output: {eval_count} rows")
print(f"Models evaluated: {model_names}")

scoring_exists = spark.catalog.tableExists(f"{out}.m5_scoring_output")
if scoring_exists:
    scoring_count = spark.table(f"{out}.m5_scoring_output").count()
    print(f"Scoring output: {scoring_count} rows")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({
    "status": "SUCCESS",
    "run_id": run_id,
    "eval_rows": eval_count,
    "models": model_names,
}))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC You ran the full CPU model set directly with `mmf_sa`, and know where its results land. **Next:** *3.3 Lab — Provision and Execute with Genie Code*, where Genie Code builds the same pipeline for you.
