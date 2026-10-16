# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 5 — Checkpoint

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

# MAGIC %run ../_includes/checks

# COMMAND ----------

checks = []

best_table = f"{out}.m5_best_models"
try:
    best_df = spark.table(best_table)
    best_count = best_df.count()
    checks.append(("Best models table exists", True, f"{best_count} rows"))
    checks.append(("Has rows", best_count > 0, ""))
except Exception as e:
    checks.append(("Best models table exists", False, str(e)))

summary_table = f"{out}.m5_evaluation_summary"
try:
    summary_count = spark.table(summary_table).count()
    checks.append(("Evaluation summary exists", True, f"{summary_count} rows"))
except Exception as e:
    checks.append(("Evaluation summary exists", False, str(e)))

# COMMAND ----------

finish("Lab 5", checks)
