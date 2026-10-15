# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 0 — Checkpoint

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

try:
    spark.sql(f"DESCRIBE SCHEMA {catalog}.{user_schema}")
    checks.append(("Schema exists", True, ""))
except Exception as e:
    checks.append(("Schema exists", False, str(e)))

for t in ["daily_train_100", "daily_train_1000"]:
    fqn = f"{catalog}.m5.{t}"
    try:
        n = spark.table(fqn).count()
        checks.append((f"Shared data {t}", n > 0, f"{n} rows"))
    except Exception as e:
        checks.append((f"Shared data {t}", False, str(e)))

# COMMAND ----------

all_pass = all(ok for _, ok, _ in checks)
for name, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} {detail}")

print(f"\nLab 0: {'PASS' if all_pass else 'FAIL'}")
dbutils.notebook.exit("PASS" if all_pass else "FAIL")
