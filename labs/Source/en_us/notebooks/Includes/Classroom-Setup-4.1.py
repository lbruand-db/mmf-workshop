# Databricks notebook source
# MAGIC %md
# MAGIC # Classroom setup — 4.1
# MAGIC
# MAGIC Creates your output schema and puts this lesson's input in place: the forecast
# MAGIC evaluation results from 3.3 (copied from the reference results if you skipped it).

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

ensure_schema()
ensure_table("m5_evaluation_output", f"{reference}.m5_evaluation_output")
