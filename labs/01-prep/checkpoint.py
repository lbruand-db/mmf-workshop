# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 1 — Checkpoint

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
table = f"{catalog}.{user_schema}.m5_train_data"

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

all_pass = all(ok for _, ok, _ in checks)
for name, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} {detail}")

print(f"\nLab 1: {'PASS' if all_pass else 'FAIL'}")
dbutils.notebook.exit("PASS" if all_pass else "FAIL")
