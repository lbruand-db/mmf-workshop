# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # 3.1 Lecture — Backtesting and Forecast Stability
# MAGIC
# MAGIC Before trusting a "best model", you need to know how it was judged. MMF judges every model on every series with a **backtest**: it pretends to stand at several moments in the past, forecasts the next days, and compares with what really happened. This lecture shows — interactively — why **how many** of those moments you use decides whether the verdict can be trusted.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Before you start: compute
# MAGIC
# MAGIC This lecture runs no Spark job: any compute works, including **Serverless**. The explorer below runs entirely in your browser.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lesson you can:
# MAGIC - Explain a rolling-origin backtest and why each window only uses data from before its cutoff.
# MAGIC - Translate MMF's `prediction_length`, `backtest_length` and `stride` into the number and position of backtest windows.
# MAGIC - Explain why a verdict based on one or two windows can be wrong, and choose settings that trade compute for stability.

# COMMAND ----------

# MAGIC %md
# MAGIC ## A. What a backtest is
# MAGIC
# MAGIC A single train/test split answers *"how did the model do on these 28 days?"* — one exam, one grade. A **rolling-origin backtest** repeats the exam: it picks several **cutoffs** in the past, and at each one it
# MAGIC
# MAGIC 1. gives the model only the data **before** the cutoff (no peeking at the future),
# MAGIC 2. forecasts the next `prediction_length` days,
# MAGIC 3. scores the forecast against what actually happened.
# MAGIC
# MAGIC In MMF, **local models** (StatsForecast: Seasonal Naive, AutoETS, …) are refitted on each window's history. **Global models** (MLForecast/LightGBM) are trained once, on the data before the first cutoff, and then predict each window from its updated history without refitting.
# MAGIC
# MAGIC ```
# MAGIC history ───────────────────────────────────────────────────────────┤ today
# MAGIC window 1   train ████████████████████████████████│ forecast ░░░░
# MAGIC window 2   train ██████████████████████████████████████│ forecast ░░░░
# MAGIC window 3   train ████████████████████████████████████████████│ forecast ░░░░
# MAGIC                                                  ↑ cutoffs, `stride` days apart
# MAGIC ```
# MAGIC
# MAGIC Each window gets one score (sMAPE by default, computed with sktime). MMF writes one row per series, model and window to the evaluation table; best-model selection — Skill 5, or lesson 4.1 — then averages each model's windows and keeps the best per series.

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. MMF's three parameters
# MAGIC
# MAGIC | Parameter | Meaning |
# MAGIC |-----------|---------|
# MAGIC | `prediction_length` | Forecast horizon: days predicted in each window (the workshop uses 28) |
# MAGIC | `backtest_length` | How far back the first cutoff is placed: the first cutoff is `backtest_length` days before the end of the data |
# MAGIC | `stride` | Days between consecutive cutoffs |
# MAGIC
# MAGIC Cutoffs fall at `n − backtest_length + k × stride` for as long as a full horizon fits before the end of the data, so
# MAGIC
# MAGIC **number of windows = ⌊(`backtest_length` − `prediction_length`) / `stride`⌋ + 1**
# MAGIC
# MAGIC | Setting | Windows | Where you meet it |
# MAGIC |---------|---------|-------------------|
# MAGIC | `backtest_length=28, stride=28` | 1 | A single train/test split |
# MAGIC | `backtest_length=56, stride=28` | 2 | This workshop's fast setting (3.2, 3.3) — chosen to fit the session |
# MAGIC | `backtest_length=90, stride=7` | 9 | MMF's M5 example; lesson 3.2's `full` setting |
# MAGIC | `backtest_length=182, stride=14` | 12 | Half a year of evidence |
# MAGIC
# MAGIC When `stride` is smaller than `prediction_length`, windows **overlap**: they share days, so they add less information than their count suggests.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Explore
# MAGIC
# MAGIC The explorer backtests two simple local models on three daily series, placing windows exactly as `mmf_sa` does (first window starts `backtest_length` days before the end; windows `stride` days apart while a full horizon fits; refit at each cutoff) and scoring them with the same sMAPE and MAE formulas:
# MAGIC - **Seasonal Naive** — next week repeats last week;
# MAGIC - **Weekday average (4 wk)** — each weekday is the average of that weekday over the last 4 weeks.
# MAGIC
# MAGIC Both capture the weekly pattern, so they are close competitors — the situation where model selection is hard. For each series you see the backtest windows and forecasts, the error in each window, and a **stability test**: the same backtest re-run on 100 *alternative histories* (same series structure, different random noise). If the same model wins almost every time, the verdict is **stable**; if it flips, a different week of data would have crowned a different model.
# MAGIC
# MAGIC **Try this:**
# MAGIC 1. Click **One window**, then **Workshop (56 / 28)**, then **MMF full (90 / 7)**. Watch the badges and the summary table.
# MAGIC 2. On series 3, compare *"2 of 2 windows agree"* with the stability percentage at the workshop setting.
# MAGIC 3. Click **New random history** a few times at **One window**, then at **Half a year**: how often does the winner of series 3 change?
# MAGIC 4. Switch the metric to **MAE** and look at series 2.

# COMMAND ----------

# MAGIC %run ../Includes/_backtest_explorer

# COMMAND ----------

displayHTML(BACKTEST_EXPLORER_HTML)

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. What you should see
# MAGIC
# MAGIC <details>
# MAGIC <summary><b>Show the answers</b></summary>
# MAGIC
# MAGIC 1. **More windows, steadier verdicts.** With one or two windows, series 3 (promotions and a level shift) crowns Seasonal Naive in only about 55–65% of the alternative histories — barely better than a coin toss. With 9 or more windows the **weekday average** wins in nearly all of them: the short backtest usually pointed to the wrong model. Series 1 is fairly stable even with one window, because the gap between the two models is clear.
# MAGIC 2. **Agreement is not stability.** At the workshop setting both windows of series 3 can agree with each other and still give a verdict that flips in almost half of the alternative histories. Two windows simply contain too little evidence — they can be unlucky together (for example, both dominated by the level shift).
# MAGIC 3. **Few windows make the answer depend on luck.** At *One window*, re-drawing the history changes the winner of series 3 often; at *Half a year* it rarely does.
# MAGIC 4. **The metric can decide the winner.** On the intermittent series, sMAPE scores an exact zero forecast on a zero-demand day as perfect, so Seasonal Naive — which copies last week's zeros — wins every time. Under MAE the two models are nearly tied, and only many windows separate them. Choosing a metric for sparse series is its own topic.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Choosing settings in practice
# MAGIC
# MAGIC - **Windows cost compute.** Each window refits every local model on every series: 9 windows cost about 4–5× as much as 2 (global models are trained once, so for them extra windows only add predictions). That is why this workshop uses 2 windows — read its winners per series as indicative, not final.
# MAGIC - **For production model selection, use more evidence:** several windows covering the seasonal events you care about (holidays, promotions), with a `stride` that is a multiple of 7 for daily data so that every window starts on the same weekday mix.
# MAGIC - **Overlapping windows** (`stride` < `prediction_length`) are cheaper per bit of coverage but not independent; prefer more distinct windows to many overlapping ones.
# MAGIC - **Look at the margin, not only the winner.** When two models are within noise of each other, either is a defensible choice; MMF's tie-break in 4.1 prefers the simpler model.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC A backtest grades each model on several past windows; the number of windows is what makes the grade trustworthy. You can now read MMF's backtest settings, predict how many windows they produce, and judge how much to trust the per-series winners. **Next:** *3.2 Demo — MMF with mmf_sa*, where these settings drive a real forecast.
