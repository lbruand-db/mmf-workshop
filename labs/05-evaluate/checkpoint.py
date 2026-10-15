# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 5 — Checkpoint

# COMMAND ----------

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("user_schema", "")

catalog = dbutils.widgets.get("catalog")
user_schema = dbutils.widgets.get("user_schema")

if not user_schema:
    user = spark.sql("select current_user() as user").collect()[0]["user"]
    user_schema = user.split("@")[0].replace(".", "_")

# COMMAND ----------

checks = []

best_table = f"{catalog}.{user_schema}.m5_best_models"
try:
    best_df = spark.table(best_table)
    best_count = best_df.count()
    checks.append(("Best models table exists", True, f"{best_count} rows"))
    checks.append(("Has rows", best_count > 0, ""))
except Exception as e:
    checks.append(("Best models table exists", False, str(e)))

summary_table = f"{catalog}.{user_schema}.m5_evaluation_summary"
try:
    summary_count = spark.table(summary_table).count()
    checks.append(("Evaluation summary exists", True, f"{summary_count} rows"))
except Exception as e:
    checks.append(("Evaluation summary exists", False, str(e)))

# COMMAND ----------

all_pass = all(ok for _, ok, _ in checks)
for name, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} {detail}")

print(f"\nLab 5: {'PASS' if all_pass else 'FAIL'}")
dbutils.notebook.exit("PASS" if all_pass else "FAIL")
