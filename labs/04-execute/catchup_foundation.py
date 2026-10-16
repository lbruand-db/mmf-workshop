# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 4 — Foundation Model Forecast (GPU)
# MAGIC
# MAGIC Runs Chronos-2 on a reduced dataset (100 series) with a shorter backtest
# MAGIC window for fast iteration. Requires a GPU cluster (`g4dn.xlarge` / T4)
# MAGIC or serverless GPU (AI Runtime with A10).
# MAGIC
# MAGIC Results append to the same evaluation/scoring tables as the CPU notebook,
# MAGIC so Lab 5 sees all model classes together.

# COMMAND ----------

# MAGIC %pip install -r /Volumes/mmf/m5/assets/wheels/requirements-foundation.txt --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid
import logging

logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)
logging.getLogger("mlflow.tracking.context.registry").setLevel(logging.ERROR)

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

dbutils.widgets.text("n_series", "100")
dbutils.widgets.text("run_id", "")
dbutils.widgets.dropdown("model", "Chronos2", ["Chronos2", "Chronos2Small", "ChronosBoltSmall", "TimesFM_2_5_200m"])

n_series = dbutils.widgets.get("n_series")
run_id = dbutils.widgets.get("run_id") or str(uuid.uuid4())
model = dbutils.widgets.get("model")

train_table = f"{source}.daily_train_{n_series}"
print(f"Train data: {train_table}")
print(f"Model: {model}")
print(f"Run ID: {run_id}")

# COMMAND ----------

_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {out}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Run foundation model
# MAGIC
# MAGIC Uses a reduced backtest (`backtest_length=56, stride=28` → 2 windows)
# MAGIC to keep runtime under ~12 min on a single T4.

# COMMAND ----------

from mmf_sa import run_forecast

run_forecast(
    spark=spark,
    train_data=train_table,
    scoring_data=train_table,
    scoring_output=f"{out}.m5_scoring_output",
    evaluation_output=f"{out}.m5_evaluation_output",
    model_output=out,
    group_id="unique_id",
    date_col="ds",
    target="y",
    freq="D",
    prediction_length=28,
    backtest_length=56,
    stride=28,
    metric="smape",
    train_predict_ratio=1,
    data_quality_check=True,
    resample=False,
    active_models=[model],
    experiment_path=f"/Users/{user_email}/mmf_m5_workshop",
    use_case_name="m5",
    run_id=run_id,
    accelerator="gpu",
)

print(f"{model} complete.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify

# COMMAND ----------

foundation_rows = spark.sql(f"""
    SELECT COUNT(*) AS n
    FROM {out}.m5_evaluation_output
    WHERE model = '{model}'
""").collect()[0]["n"]
print(f"{model} evaluation rows: {foundation_rows}")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({
    "status": "SUCCESS",
    "model": model,
    "run_id": run_id,
    "eval_rows": foundation_rows,
}))
