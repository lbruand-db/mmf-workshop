# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 0 — Checkpoint

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

# MAGIC %run ../_includes/checks

# COMMAND ----------

checks = []

try:
    spark.sql(f"DESCRIBE SCHEMA {out}")
    checks.append(("Schema exists", True, ""))
except Exception as e:
    checks.append(("Schema exists", False, str(e)))

for t in ["daily_train_100", "daily_train_1000"]:
    fqn = f"{source}.{t}"
    try:
        n = spark.table(fqn).count()
        checks.append((f"Shared data {t}", n > 0, f"{n} rows"))
    except Exception as e:
        checks.append((f"Shared data {t}", False, str(e)))

# COMMAND ----------

finish("Lab 0", checks)
