# Lab 1 — Data Preparation

## Purpose

Copy the M5 training data into your personal schema and explore its structure. This is the starting point for the forecasting pipeline — understanding the data shape, frequency, and any quality issues before running models.

## What Databricks/MMF brings

- **MMF Skill 1 (Data Preparation)** guides you through loading, inspecting, and validating time series data via Genie Code prompts.
- **Delta Lake** tables provide ACID transactions and time travel — if you make a mistake, you can always roll back.
- **Serverless compute** means zero cluster management — your SQL and Python cells run instantly without waiting for infrastructure.

## Hints

- The M5 dataset has daily granularity (`freq="D"`) with ~1,941 days per series.
- `unique_id` is the series identifier — it combines item, store, and department.
- Watch for intermittent series (lots of zeros) — they're common in retail and affect which models work best.
- Ask Genie Code: *"Show me the distribution of zero values across series"* to get a feel for data sparsity.
