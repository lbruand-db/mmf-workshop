# Databricks notebook source
# MAGIC %md
# MAGIC # Classroom setup — 3.3
# MAGIC
# MAGIC Creates your output schema and puts this lesson's input in place: the prepared
# MAGIC training data from 2.2 (copied from the shared 100-series table if you skipped it).

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

ensure_schema()
ensure_table("m5_train_data", f"{source}.daily_train_100")
