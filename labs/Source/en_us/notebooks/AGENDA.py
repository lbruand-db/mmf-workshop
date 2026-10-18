# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # Many-Model Forecasting with Genie Code
# MAGIC
# MAGIC Forecast hundreds of retail time series end-to-end — data preparation, model execution and evaluation — on Databricks, by driving the **Many-Model Forecasting (MMF)** solution accelerator in natural language with **Genie Code** and the **MMF skill**.
# MAGIC
# MAGIC You work with the **M5** dataset (daily unit sales per item and store), sampled to 100 series. Statistical models and LightGBM run in parallel on serverless compute; foundation model results are pre-computed for comparison.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prerequisites
# MAGIC
# MAGIC - Basic Databricks navigation: workspace, notebooks, Catalog Explorer
# MAGIC - Basic forecasting vocabulary: horizon, backtest, sMAPE / WAPE
# MAGIC - No prior MMF, MLflow or Spark knowledge required. Python helps but isn't required: Genie Code writes the code.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Agenda
# MAGIC
# MAGIC | # | Module | Lessons | Time |
# MAGIC |---|--------|---------|------|
# MAGIC | 1 | **[Many-Model Forecasting Foundations]($./M01 - Many-Model Forecasting Foundations)** | • [**Demo:** Genie Code and the MMF Skill]($./M01 - Many-Model Forecasting Foundations/1.2 Demo - Genie Code and the MMF Skill) | 15 min |
# MAGIC | 2 | **[Preparing Many Series]($./M02 - Preparing Many Series)** | • [**Demo:** Prep and Clean with Genie Code]($./M02 - Preparing Many Series/2.2 Demo - Prep and Clean with Genie Code) | 25 min |
# MAGIC | 3 | **[Running Forecasts at Scale]($./M03 - Running Forecasts at Scale)** | • [*Lecture:* Backtesting and Forecast Stability]($./M03 - Running Forecasts at Scale/3.1 Lecture - Backtesting and Forecast Stability) — *interactive* <br> • [**Demo:** MMF with mmf_sa]($./M03 - Running Forecasts at Scale/3.2 Demo - MMF with mmf_sa) — *instructor demo, shown while your jobs run* <br> • [**Lab:** Provision and Execute with Genie Code]($./M03 - Running Forecasts at Scale/3.3 Lab - Provision and Execute with Genie Code) <br> • [*Appendix:* Forecasting with Exogenous Variables]($./M03 - Running Forecasts at Scale/3.4 Appendix - Forecasting with Exogenous Variables) — *optional* | 30 min |
# MAGIC | 4 | **[Evaluating and Selecting Models]($./M04 - Evaluating and Selecting Models)** | • [**Lab:** Best Model per Series]($./M04 - Evaluating and Selecting Models/4.1 Lab - Best Model per Series) <br> • [*Appendix:* Choosing a Forecast Metric]($./M04 - Evaluating and Selecting Models/4.2 Appendix - Choosing a Forecast Metric) — *interactive, optional* | 30 min |
# MAGIC
# MAGIC About 2 hours with introduction and wrap-up. Forecast jobs keep running in the background: don't wait for them — the *Short on time?* cells let you carry on, and you can come back to your own results afterwards.

# COMMAND ----------

# MAGIC %md
# MAGIC ## How the lessons work
# MAGIC
# MAGIC - **Classroom setup** — the first cell of every lesson. Run it first: it prints where your outputs go and puts the lesson's inputs in place, so you can start any lesson without doing the previous ones.
# MAGIC - **Short on time?** — in lessons where Genie Code builds something, this cell puts the expected output in place in seconds.
# MAGIC - **Check your work** — the last section of every lesson prints PASS or FAIL for each expected output.
# MAGIC
# MAGIC Shared data is read-only in `mmf.m5`. Your outputs go to your own location; nothing you do affects other participants.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Requirements
# MAGIC
# MAGIC - Run every lesson on **Serverless** compute (environment version 4).
# MAGIC - Genie Code must be enabled, with the MMF skill installed in your home folder — lesson 1.2 checks this.
# MAGIC
# MAGIC See [Version Info]($./Version Info) for the course version and dataset attributions.
