# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 4 — Execute MMF Forecast (Catchup)
# MAGIC
# MAGIC Copies the reference forecast results into your schema, so you can move on
# MAGIC to Lab 5 in seconds instead of waiting for the models to run.
# MAGIC
# MAGIC The reference results were produced by `run_cpu.py` (5 local models +
# MAGIC LightGBM, 100 series, `backtest_length=90`, `stride=7`) when the workspace
# MAGIC was set up. Run `run_cpu.py` yourself to reproduce them.

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {out}")

copied = {}
for table in ["m5_evaluation_output", "m5_scoring_output"]:
    (
        spark.table(f"{reference}.{table}")
        .write.format("delta").mode("overwrite").option("overwriteSchema", "true")
        .saveAsTable(f"{out}.{table}")
    )
    copied[table] = spark.table(f"{out}.{table}").count()
    print(f"Copied {reference}.{table} -> {out}.{table} ({copied[table]} rows)")

models = sorted(r["model"] for r in spark.table(f"{out}.m5_evaluation_output").select("model").distinct().collect())
print(f"Models evaluated: {models}")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({"status": "SUCCESS", "rows": copied, "models": models}))
