# Databricks notebook source
# MAGIC %md
# MAGIC # Pre-compute Foundation Model Reference Results (CPU)
# MAGIC
# MAGIC Runs Chronos-Bolt-Small directly on CPU (no GPU required) and writes
# MAGIC results in the same schema as MMF's `run_forecast` evaluation output.
# MAGIC Saved to `mmf.m5.reference_evaluation_output` as shared reference data.
# MAGIC
# MAGIC **Runtime**: ~10–15 min on serverless CPU for 100 series, 2 backtest windows.

# COMMAND ----------

# MAGIC %pip install "chronos-forecasting[training]==2.2.2" torch --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import uuid
import numpy as np
import pandas as pd
from datetime import datetime

# COMMAND ----------

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("schema", "m5")
dbutils.widgets.text("n_series", "100")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
n_series = dbutils.widgets.get("n_series")

run_id = str(uuid.uuid4())
train_table = f"{catalog}.{schema}.daily_train_{n_series}"

print(f"Train data: {train_table}")
print(f"Run ID: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Load training data

# COMMAND ----------

df = spark.table(train_table).select("unique_id", "ds", "y").toPandas()
df["ds"] = pd.to_datetime(df["ds"])
df = df.sort_values(["unique_id", "ds"])

series_ids = df["unique_id"].unique()
print(f"Loaded {len(series_ids)} series, {len(df)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Load Chronos-Bolt-Small on CPU

# COMMAND ----------

import torch
from chronos import BaseChronosPipeline

pipeline = BaseChronosPipeline.from_pretrained(
    "amazon/chronos-bolt-small",
    device_map="cpu",
    torch_dtype=torch.float32,
)
print("Chronos-Bolt-Small loaded on CPU")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Run backtest
# MAGIC
# MAGIC Two backtest windows (backtest_length=56, stride=28, prediction_length=28).
# MAGIC For each window, hold out the last N days, predict, and compute SMAPE.

# COMMAND ----------

prediction_length = 28
backtest_length = 56
stride = 28

def smape(actual, predicted):
    denominator = (np.abs(actual) + np.abs(predicted))
    mask = denominator > 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(2.0 * np.abs(actual[mask] - predicted[mask]) / denominator[mask]))

results = []
n_windows = (backtest_length - prediction_length) // stride + 1

for i, sid in enumerate(series_ids):
    s = df[df["unique_id"] == sid].sort_values("ds")
    values = s["y"].values.astype(np.float32)
    dates = s["ds"].values

    for w in range(n_windows):
        cutoff = len(values) - backtest_length + w * stride
        if cutoff < prediction_length:
            continue

        context = torch.tensor(values[:cutoff], dtype=torch.float32)
        actual = values[cutoff:cutoff + prediction_length]

        if len(actual) < prediction_length:
            continue

        with torch.no_grad():
            forecast = pipeline.predict(
                inputs=context.unsqueeze(0),
                prediction_length=prediction_length,
            )
        # forecast shape: (1, num_quantiles, prediction_length)
        # Take the median quantile (index 4 of 9 quantiles: 0.1..0.9)
        predicted = forecast[0].numpy()
        if predicted.ndim == 2:
            predicted = predicted[predicted.shape[0] // 2]  # median quantile
        predicted = predicted[:prediction_length]

        metric_val = smape(actual, predicted)
        window_start = pd.Timestamp(dates[cutoff]).tz_localize("UTC")

        results.append({
            "unique_id": sid,
            "backtest_window_start_date": window_start.to_pydatetime(),
            "metric_name": "smape",
            "metric_value": float(metric_val),
            "forecast": [float(x) for x in predicted.tolist()],
            "actual": [float(x) for x in actual.tolist()],
            "run_id": run_id,
            "run_date": datetime.now(),
            "model": "ChronosBoltSmall",
            "use_case": "m5",
        })

    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(series_ids)} series done")

print(f"Total evaluation rows: {len(results)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Write to reference tables

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, ArrayType

eval_schema = StructType([
    StructField("unique_id", StringType()),
    StructField("backtest_window_start_date", TimestampType()),
    StructField("metric_name", StringType()),
    StructField("metric_value", DoubleType()),
    StructField("forecast", ArrayType(DoubleType())),
    StructField("actual", ArrayType(DoubleType())),
    StructField("run_id", StringType()),
    StructField("run_date", TimestampType()),
    StructField("model", StringType()),
    StructField("use_case", StringType()),
])

eval_df = spark.createDataFrame(results, schema=eval_schema)
eval_df.write.format("delta").mode("overwrite").saveAsTable(
    f"{catalog}.{schema}.reference_evaluation_output"
)

row_count = spark.table(f"{catalog}.{schema}.reference_evaluation_output").count()
print(f"Saved {row_count} rows to {catalog}.{schema}.reference_evaluation_output")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({
    "status": "SUCCESS",
    "run_id": run_id,
    "eval_rows": row_count,
    "model": "ChronosBoltSmall",
}))
