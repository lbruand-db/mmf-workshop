# Databricks notebook source
# MAGIC %md
# MAGIC # Classroom setup — 1.2
# MAGIC
# MAGIC Creates your output schema and checks that the shared M5 data is readable, and installs the MMF skill for Genie Code in your home folder.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

ensure_schema()
ensure_mmf_skill()

for t in ["daily_train_100", "daily_train_1000", "m5_static_features"]:
    try:
        print(f"  OK  {source}.{t} — {spark.table(f'{source}.{t}').count()} rows")
    except Exception as e:
        print(f"  FAIL  {source}.{t} — {e}")
