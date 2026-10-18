# Databricks notebook source
# MAGIC %md
# MAGIC # Classroom setup — 3.4
# MAGIC
# MAGIC Creates your output schema and installs the MMF skill for Genie Code. The lesson builds its own inputs
# MAGIC from the shared 100-series table, so it needs nothing from earlier lessons.

# COMMAND ----------

# MAGIC %run ./_common

# COMMAND ----------

ensure_schema()
ensure_mmf_skill()
