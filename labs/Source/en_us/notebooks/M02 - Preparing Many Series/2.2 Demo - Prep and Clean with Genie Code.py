# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 2.2 Demo — Prep and Clean with Genie Code
# MAGIC
# MAGIC Prepare the M5 training data in your own schema with **MMF Skill 1**, and explore its structure: shape, frequency and quality issues to know about before running models.
# MAGIC
# MAGIC **What Databricks brings**
# MAGIC - **MMF Skill 1 (prep and clean)** guides loading, inspecting and validating time series through Genie Code.
# MAGIC - **Delta Lake** tables are transactional and keep history — if you make a mistake, you can roll back.
# MAGIC - **Serverless compute**: no cluster to manage; cells run right away.

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
# MAGIC - Drive MMF Skill 1 from Genie Code to produce a training table.
# MAGIC - Answer the skill's decision points (location, source table, frequency, regressors).
# MAGIC - Recognise intermittent series and why they matter for model choice.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom setup

# COMMAND ----------

# MAGIC %run ../Includes/Classroom-Setup-2.2

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. Prepare the data with Genie Code
# MAGIC
# MAGIC 1. In Genie Code, type `/prep-and-clean-data`.
# MAGIC 2. When it asks, use:
# MAGIC    - catalog and schema: **your output location** (printed by the setup cell above)
# MAGIC    - source table: **`mmf.m5.daily_train_100`**
# MAGIC    - use case: **`m5`**, daily frequency (`D`)
# MAGIC    - dynamic regressors: **no**
# MAGIC 3. The output is the table `m5_train_data` in your schema.

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Explore
# MAGIC
# MAGIC - M5 is daily (`freq="D"`), with about 1,941 days per series.
# MAGIC - `unique_id` identifies a series: one item in one store.
# MAGIC - Many retail series are **intermittent** (mostly zeros), which changes which models work best.
# MAGIC - Ask Genie Code: *Show me the distribution of zero values across series.*

# COMMAND ----------

# MAGIC %md
# MAGIC ## Short on time?
# MAGIC
# MAGIC Run the next cell to put `m5_train_data` in place without the agent. The M5 samples are already clean, so this is a straight copy.

# COMMAND ----------

dbutils.widgets.text("n_series", "100")
n_series = dbutils.widgets.get("n_series")

rows = copy_table(f"{source}.daily_train_{n_series}", "m5_train_data")
series = spark.table(f"{out}.m5_train_data").select("unique_id").distinct().count()
print(f"Wrote {out}.m5_train_data: {series} series, {rows} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check your work

# COMMAND ----------

# MAGIC %run ../Includes/_checks

# COMMAND ----------

checks = []
table = f"{out}.m5_train_data"

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

finish("2.2", checks)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC You have `m5_train_data` in your schema and a feel for the data — including how many series are mostly zeros. **Next:** *3.2 Demo — MMF with mmf_sa*.
