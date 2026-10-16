# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 1 — Checkpoint

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

# MAGIC %run ../_includes/checks

# COMMAND ----------

checks = []
table = f"{out}.m5_train_data"

try:
    df = spark.table(table)
    n = df.count()
    checks.append(("Table exists", True, f"{n} rows"))
except Exception as e:
    checks.append(("Table exists", False, str(e)))
    n = 0

if n > 0:
    cols = set(df.columns)
    for required in ["unique_id", "ds", "y"]:
        checks.append((f"Column '{required}'", required in cols, ""))

    series = df.select("unique_id").distinct().count()
    checks.append(("Series count > 0", series > 0, f"{series} series"))

# COMMAND ----------

finish("Lab 1", checks)
