# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 4.1 Lab — Best Model per Series
# MAGIC
# MAGIC Select the best model per series, build a leaderboard, and see where each
# MAGIC model class wins — the answer to *"which model should we deploy for each product?"*
# MAGIC
# MAGIC Automatically merges pre-computed foundation model results (from
# MAGIC `mmf.m5.reference_evaluation_output`) with participant CPU results,
# MAGIC so every participant sees how foundation models compare — even without
# MAGIC GPU access.
# MAGIC
# MAGIC Best-model selection averages the metric over backtest windows and breaks ties
# MAGIC in favour of simpler model classes (cheaper to run in production).

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
# MAGIC - Select the best model per series from backtest results.
# MAGIC - Build a leaderboard of model wins.
# MAGIC - Compare statistical, ML and foundation models, and spot the series every model struggles with.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Classroom setup

# COMMAND ----------

# MAGIC %run ../Includes/Classroom-Setup-4.1

# COMMAND ----------

dbutils.widgets.text("metric", "smape")
metric = dbutils.widgets.get("metric")
print(f"Metric: {metric}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Your evaluation results

# COMMAND ----------

eval_table = f"{out}.m5_evaluation_output"
eval_df = spark.table(eval_table)
eval_count = eval_df.count()

models_present = [r["model"] for r in eval_df.select("model").distinct().collect()]
print(f"Evaluation rows: {eval_count}")
print(f"Models from 3.3: {sorted(models_present)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Merge foundation model reference results
# MAGIC
# MAGIC If the shared schema has pre-computed foundation model results
# MAGIC (`reference_evaluation_output`), append them to the participant's
# MAGIC evaluation table. This gives a complete picture across all model
# MAGIC classes without requiring GPU access.

# COMMAND ----------

ref_table = f"{source}.reference_evaluation_output"
ref_added = 0

try:
    ref_df = spark.table(ref_table)
    ref_models = [r["model"] for r in ref_df.select("model").distinct().collect()]

    already_have = set(models_present)
    new_models = [m for m in ref_models if m not in already_have]

    if new_models:
        ref_subset = ref_df.filter(ref_df.model.isin(new_models))

        common_cols = list(set(eval_df.columns) & set(ref_subset.columns))
        ref_subset.select(common_cols).write.format("delta").mode("append").saveAsTable(eval_table)

        ref_added = ref_subset.count()
        print(f"Appended {ref_added} reference rows for models: {new_models}")
    else:
        print(f"Foundation models {ref_models} already in evaluation table — skipping merge")
except Exception as e:
    print(f"No reference results found ({e}) — continuing with CPU models only")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Best model per series
# MAGIC
# MAGIC For each `unique_id`, pick the model with the lowest average metric across
# MAGIC all backtest windows. Ties break in favour of simpler/cheaper model classes:
# MAGIC StatsForecast (tier 1) > MLForecast (tier 2) > NeuralForecast (tier 3) > Foundation (tier 4).

# COMMAND ----------

combined_table = f"{out}.m5_evaluation_output"

spark.sql(f"""
CREATE OR REPLACE TABLE {out}.m5_best_models AS
WITH avg_metrics AS (
    SELECT
        unique_id,
        model,
        AVG(metric_value) AS avg_metric,
        COUNT(*) AS n_windows
    FROM {combined_table}
    WHERE metric_name = '{metric}'
    GROUP BY unique_id, model
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY unique_id
            ORDER BY
                avg_metric ASC,
                CASE
                    WHEN model LIKE 'StatsForecast%' OR model LIKE 'SKTime%' THEN 1
                    WHEN model LIKE 'MLForecast%' THEN 2
                    WHEN model LIKE 'NeuralForecast%' THEN 3
                    ELSE 4
                END ASC
        ) AS rank
    FROM avg_metrics
)
SELECT
    unique_id,
    model AS best_model,
    avg_metric AS best_metric,
    n_windows
FROM ranked
WHERE rank = 1
""")

best_count = spark.table(f"{out}.m5_best_models").count()
print(f"Best models selected for {best_count} series")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Evaluation summary (wins per model)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE TABLE {out}.m5_evaluation_summary AS
WITH best AS (
    SELECT * FROM {out}.m5_best_models
),
total AS (
    SELECT COUNT(*) AS total_series FROM best
)
SELECT
    b.best_model AS model,
    COUNT(*) AS wins_count,
    ROUND(COUNT(*) * 100.0 / t.total_series, 1) AS wins_pct,
    ROUND(AVG(b.best_metric), 4) AS avg_metric
FROM best b
CROSS JOIN total t
GROUP BY b.best_model, t.total_series
ORDER BY wins_count DESC
""")

display(spark.table(f"{out}.m5_evaluation_summary"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Top-level stats

# COMMAND ----------

overall = spark.sql(f"""
SELECT
    COUNT(*) AS total_series,
    COUNT(DISTINCT best_model) AS n_models,
    ROUND(AVG(best_metric), 4) AS overall_avg_metric,
    ROUND(PERCENTILE(best_metric, 0.5), 4) AS median_metric,
    ROUND(MAX(best_metric), 4) AS worst_metric
FROM {out}.m5_best_models
""")
display(overall)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Worst-performing series (top 10)

# COMMAND ----------

display(spark.sql(f"""
SELECT *
FROM {out}.m5_best_models
ORDER BY best_metric DESC
LIMIT 10
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Ask Genie Code about the results
# MAGIC
# MAGIC - *Which model wins most often?*
# MAGIC - *Show me series where the foundation model beats all statistical models.*
# MAGIC - *What do the worst-performing series have in common?*
# MAGIC
# MAGIC Worst-performing series are often intermittent items where every model struggles;
# MAGIC in production you might route them to a dedicated model (e.g. Croston) or a simple fallback.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check your work

# COMMAND ----------

# MAGIC %run ../Includes/_checks

# COMMAND ----------

checks = []

best_table = f"{out}.m5_best_models"
try:
    best_count = spark.table(best_table).count()
    checks.append(("Best models table exists", True, f"{best_count} rows"))
    checks.append(("Has rows", best_count > 0, ""))
except Exception as e:
    checks.append(("Best models table exists", False, str(e)))

summary_table = f"{out}.m5_evaluation_summary"
try:
    summary_count = spark.table(summary_table).count()
    checks.append(("Evaluation summary exists", True, f"{summary_count} rows"))
except Exception as e:
    checks.append(("Evaluation summary exists", False, str(e)))

finish("4.1", checks)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC You have a best model per series and a leaderboard across model classes — the basis for deciding what to deploy for each product. This is the end of the core course.
