# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 1 — Prep & Clean (Catchup)
# MAGIC
# MAGIC Copies the M5 training data into the participant's schema as `m5_train_data`.
# MAGIC M5 data is already clean (no nulls, no anomalies in the sampled sets),
# MAGIC so for catchup purposes this is a direct copy.
# MAGIC
# MAGIC When participants use the agent (Skill 1), the agent runs imputation,
# MAGIC anomaly capping and produces a reproducibility notebook.

# COMMAND ----------

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("user_schema", "")
dbutils.widgets.text("source_schema", "m5")
dbutils.widgets.text("n_series", "1000")

catalog = dbutils.widgets.get("catalog")
user_schema = dbutils.widgets.get("user_schema")
source_schema = dbutils.widgets.get("source_schema")
n_series = dbutils.widgets.get("n_series")

if not user_schema:
    user = spark.sql("select current_user() as user").collect()[0]["user"]
    user_schema = user.split("@")[0].replace(".", "_")

source_table = f"{catalog}.{source_schema}.daily_train_{n_series}"
target_table = f"{catalog}.{user_schema}.m5_train_data"

print(f"Source: {source_table}")
print(f"Target: {target_table}")

# COMMAND ----------

_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{user_schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Copy training data

# COMMAND ----------

(
    spark.table(source_table)
    .write.format("delta").mode("overwrite")
    .saveAsTable(target_table)
)

count = spark.table(target_table).count()
series = spark.table(target_table).select("unique_id").distinct().count()
print(f"Wrote {target_table}: {series} series, {count} rows")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({"status": "SUCCESS", "table": target_table, "series": series, "rows": count}))
