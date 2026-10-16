# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 1.2 Demo — Genie Code and the MMF Skill
# MAGIC
# MAGIC Check that your environment is ready: your output schema exists, the shared M5 data is readable, and the MMF skill is installed for Genie Code.
# MAGIC
# MAGIC **What Databricks brings**
# MAGIC - **Unity Catalog** gives you your own output location, with shared read-only access to the M5 data — no copies, no permission setup.
# MAGIC - **Genie Code skills** let you drive the MMF pipeline in natural language instead of writing boilerplate code.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Before you start: compute
# MAGIC
# MAGIC Select **Serverless** in the compute drop-down at the top right of the notebook before running any cell.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lesson you can:
# MAGIC - Check that your output location exists and the shared M5 data is readable.
# MAGIC - Confirm Genie Code can see the MMF skill.
# MAGIC - Explain where your outputs go and why they don't affect other participants.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom setup

# COMMAND ----------

# MAGIC %run ../Includes/Classroom-Setup-1.2

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Check the MMF skill files
# MAGIC
# MAGIC The Classroom setup installed the skill in your home folder: the bundle in `.assistant/skills/` and the agent instructions in `.assistant_instructions.md`. This cell checks the files are there — it doesn't prove Genie Code has loaded them (section B does).

# COMMAND ----------

skill_path = f"/Users/{user_email}/.assistant/skills/SKILL.md"

try:
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    skill_installed = _WorkspaceFiles(ctx.apiUrl().get(), ctx.apiToken().get()).exists(skill_path)
    if skill_installed:
        print(f"  OK  Skill file found at {skill_path}")
    else:
        print(f"  WARN  Skill file not found at {skill_path}")
        print(f"        Re-run the Classroom setup cell; if it still fails, ask the instructor.")
except Exception as e:
    skill_installed = None
    print(f"  SKIP  Could not check skill path: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Ask Genie Code
# MAGIC
# MAGIC 1. Open **Genie Code** (the assistant panel).
# MAGIC 2. Ask: *What skills do you have access to?*
# MAGIC 3. You should see the **Many-Model Forecasting** skill and its sub-skills. If not, close and reopen the Genie Code panel; if it's still missing, ask the instructor.
# MAGIC
# MAGIC Every lesson prints where your outputs go. Nothing you do affects other participants.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check your work

# COMMAND ----------

# MAGIC %run ../Includes/_checks

# COMMAND ----------

checks = []

checks.append(("MMF skill installed", bool(skill_installed), skill_path))

try:
    spark.sql(f"DESCRIBE SCHEMA {out}")
    checks.append(("Output schema exists", True, out))
except Exception as e:
    checks.append(("Output schema exists", False, str(e)))

for t in ["daily_train_100", "daily_train_1000"]:
    fqn = f"{source}.{t}"
    try:
        n = spark.table(fqn).count()
        checks.append((f"Shared data {t}", n > 0, f"{n} rows"))
    except Exception as e:
        checks.append((f"Shared data {t}", False, str(e)))

finish("1.2", checks)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC Your environment is ready: you have an output location, read access to the shared M5 data, and the MMF skill in Genie Code. **Next:** *2.2 Demo — Prep and Clean with Genie Code*.
