# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # Course information
# MAGIC
# MAGIC * Name: **{{course_name}}**
# MAGIC * Version: **{{version_number}}**
# MAGIC * Build: **{{build_id}}**
# MAGIC * Source commit: [{{commit}}]({{commit_url}})
# MAGIC * Built on: **{{built_on}}**
# MAGIC
# MAGIC {{dirty_note}}
# MAGIC
# MAGIC Quote the **Build** when you report a problem with the course.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dataset attributions
# MAGIC
# MAGIC Run the next cell for the source and terms of the datasets used in this course.

# COMMAND ----------

# MAGIC %run ./Includes/Print-Dataset-Copyrights
