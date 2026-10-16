# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 4 — Execute MMF Forecast (CPU models)
# MAGIC
# MAGIC Runs the workshop model set on serverless CPU:
# MAGIC - **Local**: SeasonalNaive, AutoETS, AutoTheta, CrostonOptimized, TSB
# MAGIC - **Global ML**: LightGBM (MLForecast)
# MAGIC
# MAGIC Foundation models run separately on GPU (see `catchup_foundation.py`).
# MAGIC
# MAGIC This notebook is both the **catchup/bootstrap** (run it to get Lab 4
# MAGIC outputs without using the agent) and the **reference solution**.

# COMMAND ----------

# MAGIC %pip install "mmf_sa[local] @ git+https://github.com/databricks-industry-solutions/many-model-forecasting.git" "mmf_sa[global] @ git+https://github.com/databricks-industry-solutions/many-model-forecasting.git" --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid
import logging

logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

dbutils.widgets.text("n_series", "1000")
dbutils.widgets.text("run_id", "")

n_series = dbutils.widgets.get("n_series")
run_id = dbutils.widgets.get("run_id") or str(uuid.uuid4())

train_table = f"{source}.daily_train_{n_series}"
print(f"Train data: {train_table}")
print(f"Run ID: {run_id}")

# COMMAND ----------

_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {out}")

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
