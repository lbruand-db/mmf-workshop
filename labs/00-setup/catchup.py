# Databricks notebook source
# MAGIC %md
# MAGIC # Lab 0 — Setup Verification
# MAGIC
# MAGIC Creates the participant's schema and verifies the MMF skill is installed.

# COMMAND ----------

# MAGIC %run ../_includes/config

# COMMAND ----------

# MAGIC %md
# MAGIC ### Create user schema
# MAGIC
# MAGIC Only the schema is created here — never a catalog. On Vocareum, catalogs a
# MAGIC learner creates are dropped when that learner's lab ends.

# COMMAND ----------

_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {out}")
print(f"Schema {out} ready.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify shared M5 data is accessible

# COMMAND ----------

tables_to_check = [
    f"{source}.daily_train_100",
    f"{source}.daily_train_1000",
    f"{source}.m5_static_features",
]

all_ok = True
for t in tables_to_check:
    try:
        count = spark.table(t).count()
        print(f"  OK  {t} — {count} rows")
    except Exception as e:
        print(f"  FAIL  {t} — {e}")
        all_ok = False

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify skill installation
# MAGIC
# MAGIC Check that the MMF skill files exist in the user's workspace folder.
# MAGIC (This cell uses `dbutils.notebook` to check paths — it does not verify
# MAGIC that Genie Code has actually loaded the skill.)

# COMMAND ----------

skill_path = f"/Users/{user_email}/.assistant/skills/SKILL.md"

try:
    import requests, os
    host = spark.conf.get("spark.databricks.workspaceUrl")
    token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
    resp = requests.get(
        f"https://{host}/api/2.0/workspace/get-status",
        headers={"Authorization": f"Bearer {token}"},
        json={"path": skill_path},
    )
    if resp.status_code == 200:
        print(f"  OK  Skill file found at {skill_path}")
    else:
        print(f"  WARN  Skill file not found at {skill_path}")
        print(f"        Open Genie Code and ask: 'What skills do you have access to?'")
        print(f"        If the MMF skill is not listed, ask the instructor to re-run setup/user_setup")
except Exception as e:
    print(f"  SKIP  Could not check skill path: {e}")
    print(f"        Manually verify in Genie Code: 'What skills do you have access to?'")

# COMMAND ----------

status = "PASS" if all_ok else "FAIL"
print(f"\nLab 0: {status}")
dbutils.notebook.exit(status)
