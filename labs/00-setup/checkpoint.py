# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 0 — Checkpoint

# COMMAND ----------

# MAGIC %run ../_includes/config

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

all_pass = all(ok for _, ok, _ in checks)
for name, ok, detail in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name} {detail}")

print(f"\nLab 0: {'PASS' if all_pass else 'FAIL'}")
dbutils.notebook.exit("PASS" if all_pass else "FAIL")
