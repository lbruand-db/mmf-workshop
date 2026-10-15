# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 4 — Checkpoint

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

eval_table = f"{catalog}.{user_schema}.m5_evaluation_output"
try:
    eval_df = spark.table(eval_table)
    eval_count = eval_df.count()
    checks.append(("Evaluation table exists", True, f"{eval_count} rows"))

    models = [r["model"] for r in eval_df.select("model").distinct().collect()]
    checks.append(("At least 2 models", len(models) >= 2, f"{sorted(models)}"))
except Exception as e:
    checks.append(("Evaluation table exists", False, str(e)))

scoring_table = f"{catalog}.{user_schema}.m5_scoring_output"
try:
    scoring_count = spark.table(scoring_table).count()
    checks.append(("Scoring table exists", True, f"{scoring_count} rows"))
except Exception:
    checks.append(("Scoring table exists", False, "optional — may not exist if scoring_data was None"))

# COMMAND ----------

all_pass = all(ok for _, ok, _ in checks)
for name, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} {detail}")

print(f"\nLab 4: {'PASS' if all_pass else 'FAIL'}")
dbutils.notebook.exit("PASS" if all_pass else "FAIL")
