# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 4 — Checkpoint

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

# MAGIC %run ../_includes/checks

# COMMAND ----------

checks = []

eval_table = f"{out}.m5_evaluation_output"
try:
    eval_df = spark.table(eval_table)
    eval_count = eval_df.count()
    checks.append(("Evaluation table exists", True, f"{eval_count} rows"))

    models = [r["model"] for r in eval_df.select("model").distinct().collect()]
    checks.append(("At least 2 models", len(models) >= 2, f"{sorted(models)}"))
except Exception as e:
    checks.append(("Evaluation table exists", False, str(e)))

scoring_table = f"{out}.m5_scoring_output"
try:
    scoring_count = spark.table(scoring_table).count()
    checks.append(("Scoring table exists", True, f"{scoring_count} rows"))
except Exception as e:
    checks.append(("Scoring table exists", False, str(e)))

# COMMAND ----------

finish("Lab 4", checks)
