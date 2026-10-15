# Databricks notebook source
# MAGIC %md
# MAGIC # Pre-compute Foundation Model Reference Results (CPU)
# MAGIC
# MAGIC Runs Chronos-2 on 100 series using CPU inference (no GPU required).
# MAGIC Saves results to the shared `m5` schema as reference data that any
# MAGIC participant can use in Lab 5 without needing GPU access.
# MAGIC
# MAGIC **Runtime**: ~15–25 min on serverless CPU (backtest_length=56, stride=28).

# COMMAND ----------

# MAGIC %pip install "mmf_sa[foundation] @ git+https://github.com/databricks-industry-solutions/many-model-forecasting.git" --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid
import logging

logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)
logging.getLogger("mlflow.tracking.context.registry").setLevel(logging.ERROR)

# COMMAND ----------

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("schema", "m5")
dbutils.widgets.text("n_series", "100")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
n_series = dbutils.widgets.get("n_series")

run_id = str(uuid.uuid4())
train_table = f"{catalog}.{schema}.daily_train_{n_series}"

print(f"Train data: {train_table}")
print(f"Output: {catalog}.{schema}.reference_evaluation_output")
print(f"Run ID: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Run Chronos-2 on CPU
# MAGIC
# MAGIC Uses `accelerator="cpu"` — slower than GPU but works on any serverless
# MAGIC environment. Reduced backtest (56 days, stride 28 → 2 windows) keeps
# MAGIC total runtime under ~25 min.

# COMMAND ----------

from mmf_sa import run_forecast

user_email = spark.sql("select current_user() as user").collect()[0]["user"]

run_forecast(
    spark=spark,
    train_data=train_table,
    scoring_data=train_table,
    scoring_output=f"{catalog}.{schema}.reference_scoring_output",
    evaluation_output=f"{catalog}.{schema}.reference_evaluation_output",
    model_output=f"{catalog}.{schema}",
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
    active_models=["Chronos2"],
    experiment_path=f"/Users/{user_email}/mmf_m5_workshop",
    use_case_name="m5",
    run_id=run_id,
    accelerator="cpu",
)

print("Chronos-2 (CPU) complete.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify

# COMMAND ----------

ref_rows = spark.sql(f"""
    SELECT model, COUNT(*) AS n
    FROM {catalog}.{schema}.reference_evaluation_output
    GROUP BY model
""")
ref_rows.show()

total = ref_rows.collect()[0]["n"]

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({
    "status": "SUCCESS",
    "run_id": run_id,
    "eval_rows": total,
}))
