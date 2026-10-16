# Databricks notebook source
# MAGIC %md
# MAGIC # M5 Data Load — MMF Workshop Setup
# MAGIC
# MAGIC Loads the M5 Walmart competition dataset and writes sampled Delta tables
# MAGIC for the workshop. Run this **once** as an admin before the session.
# MAGIC
# MAGIC **Memory-optimised:** loads M5, samples early, frees memory between writes.
# MAGIC
# MAGIC Raw M5 files are cached under `cache_dir` (`workspace_setup` passes the
# MAGIC `assets` volume). If `{cache_dir}/m5/datasets` already exists, nothing is
# MAGIC downloaded — pre-stage it there for an offline setup.

# COMMAND ----------

# MAGIC %pip install datasetsforecast==0.0.8 --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("schema", "m5")
dbutils.widgets.text("cache_dir", "")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
cache_dir = dbutils.widgets.get("cache_dir")

# COMMAND ----------

_ = spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
print(f"Using {catalog}.{schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Load M5 — target only (lightweight)

# COMMAND ----------

import gc
import pathlib
import random
import numpy as np
import pandas as pd
from datasetsforecast.m5 import M5

df_target, df_exogenous, static_features = M5.load(directory=cache_dir or str(pathlib.Path.home()))

# Spark's Arrow bridge doesn't support unsigned int types — cast to signed
for df in [df_target, df_exogenous, static_features]:
    for col in df.columns:
        if df[col].dtype == np.uint8:
            df[col] = df[col].astype(np.int16)
        elif df[col].dtype == np.uint16:
            df[col] = df[col].astype(np.int32)
        elif df[col].dtype == np.uint32:
            df[col] = df[col].astype(np.int64)

print(f"Target rows: {len(df_target)}, Exogenous rows: {len(df_exogenous)}")
print(f"Static features: {len(static_features)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Write static features first (small table)

# COMMAND ----------

(
    spark.createDataFrame(static_features)
    .write.format("delta").mode("overwrite")
    .saveAsTable(f"{catalog}.{schema}.m5_static_features")
)
print(f"Saved {catalog}.{schema}.m5_static_features ({len(static_features)} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Determine sample IDs before merging

# COMMAND ----------

random.seed(7)
unique_ids = sorted(df_target["unique_id"].unique().tolist())
print(f"Total series: {len(unique_ids)}")

ids_100 = set(random.sample(unique_ids, 100))
ids_1000 = set(random.sample(unique_ids, 1000))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Write 100-series table
# MAGIC Merge only the 100-series subset to keep memory low.

# COMMAND ----------

target_100 = df_target[df_target["unique_id"].isin(ids_100)]
exog_100 = df_exogenous[df_exogenous["unique_id"].isin(ids_100)]
daily_100 = pd.merge(target_100, exog_100, on=["unique_id", "ds"], how="inner")
del target_100, exog_100

(
    spark.createDataFrame(daily_100)
    .write.format("delta").mode("overwrite")
    .saveAsTable(f"{catalog}.{schema}.daily_train_100")
)
print(f"Saved daily_train_100 — {daily_100['unique_id'].nunique()} series, {len(daily_100)} rows")
del daily_100
gc.collect()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Write 1000-series table

# COMMAND ----------

target_1000 = df_target[df_target["unique_id"].isin(ids_1000)]
exog_1000 = df_exogenous[df_exogenous["unique_id"].isin(ids_1000)]
daily_1000 = pd.merge(target_1000, exog_1000, on=["unique_id", "ds"], how="inner")
del target_1000, exog_1000

(
    spark.createDataFrame(daily_1000)
    .write.format("delta").mode("overwrite")
    .saveAsTable(f"{catalog}.{schema}.daily_train_1000")
)
print(f"Saved daily_train_1000 — {daily_1000['unique_id'].nunique()} series, {len(daily_1000)} rows")
del daily_1000
gc.collect()

# COMMAND ----------

# MAGIC %md
# MAGIC ### Free remaining memory

# COMMAND ----------

del df_target, df_exogenous, static_features
gc.collect()
print("Memory freed.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify

# COMMAND ----------

for table_name in ["m5_static_features", "daily_train_100", "daily_train_1000"]:
    count = spark.table(f"{catalog}.{schema}.{table_name}").count()
    print(f"  {table_name}: {count} rows")

print("\nData load complete.")
dbutils.notebook.exit("SUCCESS")
