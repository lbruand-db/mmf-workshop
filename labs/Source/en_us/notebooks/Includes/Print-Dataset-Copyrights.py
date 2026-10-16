# Databricks notebook source
DATASETS = [
    {
        "name": "M5 Forecasting (Walmart unit sales)",
        "used_as": "mmf.m5.daily_train_100, daily_train_1000, m5_static_features",
        "source": "M5 Forecasting Competition, organised by the Makridakis Open Forecasting Center "
                  "(University of Nicosia) with data provided by Walmart",
        "obtained_via": "Nixtla datasetsforecast 0.0.8 (M5.load)",
        "terms": "Use is subject to the M5 competition's data terms. Check them before redistributing the data.",
    },
]

for d in DATASETS:
    print(d["name"])
    for key in ["used_as", "source", "obtained_via", "terms"]:
        print(f"  {key.replace('_', ' ').capitalize()}: {d[key]}")
