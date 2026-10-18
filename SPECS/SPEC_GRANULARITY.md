# SPEC — Choosing Forecast Granularity

| | |
|---|---|
| **TODO item** | Choosing the forecast granularity: daily vs weekly vs monthly, item vs item × store — temporal aggregation for intermittent series (MMF ships weekly / monthly configs); possibly an interactive widget like 3.1 / 4.2 |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | 2.5 Appendix — Choosing the Forecast Granularity (elective) |
| **Type / time** | Lecture (20 min) + optional widget; no hands-on lab in initial scope |
| **Compute** | Serverless CPU (if interactive exploration) or none (slides only) |

## 1. Goal and learner outcomes

By the end of this lesson you can:

- Explain the trade-off between forecasting at different granularities: daily vs weekly vs monthly, individual item vs item × store aggregates.
- Identify when granularity matters: intermittent series (sparse demand) benefit from aggregation; regular series are indifferent.
- Apply MMF's weekly and monthly configuration files to recast daily M5 data and run a multi-horizon forecast.
- Measure the impact on accuracy: does forecasting weekly and then disaggregating to daily improve sMAPE vs forecasting daily directly?
- Design your own aggregation strategy for production: trade-off between stability (more data per period) and accuracy (must disaggregate later).

## 2. Background — what MMF supports

**MMF ships three frequency configurations:**

- **Daily** (`forecasting_conf_daily.yaml`): `freq='D'`, season_length=7 (weekly), lags=[1, 7, 14, 28], prediction_length=28 (28 days ahead).
- **Weekly** (`forecasting_conf_weekly.yaml`): `freq='W'`, season_length=4 (52 weeks in a year / 13, rounded), lags=[1, 4, 13, 26, 52], prediction_length=13 (13 weeks ahead, ~91 days).
- **Monthly** (`forecasting_conf_monthly.yaml`): `freq='M'`, season_length=12 (months), lags=[1, 3, 12], prediction_length=12 (12 months ahead, ~365 days).
- **Hourly** (`forecasting_conf_hourly.yaml`): `freq='H'`, season_length=24 (daily), for high-frequency data.

**How aggregation works in practice:**

1. **Resample:** daily M5 data to weekly or monthly frequency using pandas / Spark `resample()` with aggregation rule (usually `sum()` for sales).
2. **Run MMF:** execute the forecast with the weekly/monthly config on resampled data.
3. **Disaggregate (optional):** convert weekly forecasts back to daily using proportional allocation or a statistical model.

**Static features across granularities:**

`m5_static_features` (item, dept, cat, store, state) remain the same regardless of granularity. A daily and weekly forecast for the same item × store share the same metadata.

**Resample behavior:**

- `resample('W')` in Databricks / Spark groups data into weeks (by default, ending on Sunday). Ensure consistent week boundaries across all series.
- `resample('M')` groups by calendar month.
- For intermittent series (zero-heavy), resampling smooths the data: weekly aggregation combines seven zero-heavy days into one week with a few sales, reducing sparsity.

## 3. Proposed content

### Section A. Why granularity matters (10 min, lecture)

**The central question:** Should you forecast daily or weekly (or monthly)?

**Factors that favor aggregation (coarser granularity):**

1. **Intermittent or zero-heavy series:** A slow-moving item might have zero sales on 6 out of 7 days, then a restock on day 7. Modeling daily zeros is hard for statistical and ML models; weekly aggregates are more stable. Example: M5 slow-moving items, spare parts, seasonal goods.
   
2. **Noise and signal:** High-frequency noise (random daily fluctuations) is averaged out by aggregation. The true signal (weekly or monthly trend) emerges. Example: a store's traffic might fluctuate daily but be predictable weekly.

3. **Reduced dimensionality:** Fewer forecast steps. Daily forecast: 28 steps ahead; weekly: 13; monthly: 12. Fewer steps = more stable models, faster inference.

4. **Data efficiency:** If a series has 200 days of history, that's 200 data points for daily forecasting, but only ~29 weeks for weekly. For short histories, weekly provides more stability per unit of time.

**Factors that favor finer granularity (daily):**

1. **Business requirement:** You need daily forecasts (store inventory, supply chain dispatch). Disaggregating from weekly to daily introduces model error; better to forecast daily directly.

2. **Clean, abundant data:** A well-established product with strong seasonality (e.g., soft drinks in M5) is easy to forecast daily. No need to aggregate.

3. **Exogenous regressors at daily frequency:** If you have daily weather, promotions, or events, you can use them in a daily forecast. Weekly aggregation loses the detail.

4. **Speed and cost:** Daily forecasts on a large dataset are cheaper per unit time than weekly + disaggregation (you avoid the extra ETL).

**Decision framework:**

| Series characteristic | Recommendation |
|------------------------|-----------------|
| **Intermittent or sparse** (>50% zeros) | Forecast weekly or monthly, then disaggregate or aggregate up to planning horizon |
| **Regular, abundant data** (clean daily pattern, >100 obs.) | Forecast daily; aggregation won't help |
| **Short history** (<50 observations) | Aggregate to weekly/monthly for stability |
| **Business needs daily forecasts** | Forecast daily; disaggregation adds error |
| **Business needs weekly/monthly** | Aggregate naturally; no disaggregation error |

### Section B. Temporal aggregation in MMF (10 min, conceptual + config)

**The three configs side-by-side:**

Show a table comparing `forecasting_conf_daily.yaml`, `_weekly.yaml`, `_monthly.yaml`:

| Aspect | Daily | Weekly | Monthly |
|--------|-------|--------|---------|
| `freq` | `D` | `W` | `M` |
| `season_length` | 7 | 4 | 12 |
| `lags` | [1, 7, 14, 28] | [1, 4, 13, 26, 52] | [1, 3, 12] |
| `prediction_length` | 28 | 13 | 12 |
| Horizon (approx.) | 4 weeks | 13 weeks | 12 months |

**What's happening:**

- **season_length:** the period of repetition. Daily has a 7-day week; weekly has a 52-week year ÷ 13 ≈ 4-week "season" (not a calendar concept, just the periodicity used by ARIMA and ETS).
- **lags:** features for LightGBM. Daily lags 1, 7, 14, 28 days capture short-term, weekly, bi-weekly, monthly patterns. Weekly lags 1, 4, 13 weeks capture short-term, monthly, quarterly patterns.
- **prediction_length:** matches the horizon. 28 daily = ~4 weeks; 13 weekly = ~13 weeks = ~3 months. Ensure it matches your business requirement.

**Resampling in practice:**

```python
# Daily to weekly
daily_df = spark.table(f"{catalog}.{schema}.m5_train_data")  # unique_id, ds, y
weekly_df = daily_df.groupBy("unique_id", F.date_trunc("week", "ds").alias("ds")).agg(
    F.sum("y").alias("y")
).orderBy("unique_id", "ds")

# Run MMF with forecasting_conf_weekly.yaml
```

**Key caveat:** resampling on different series may produce different week boundaries if done naively. Use a deterministic cutoff (e.g., "weeks starting Monday" or `F.date_trunc('week', F.to_date(F.col("ds")))`).

### Section C. Live demo: daily vs weekly on M5 (10 min, optional demo or pre-recorded)

**Instructor runs MMF twice:**

1. **Daily forecast:** 100 series, `backtest_length=56, stride=28` (2 windows), `forecasting_conf_daily.yaml`. Runtime: ~5 min.
2. **Weekly forecast:** same 100 series (resampled to weekly), same backtest parameters, `forecasting_conf_weekly.yaml`. Runtime: ~3 min (fewer steps).

**Compare the results:**

- **sMAPE by series:** plot or table showing daily vs weekly. Expectation: intermittent series improve with weekly; regular series are unchanged or slightly worse (disaggregation error if they have one).
- **Per-model comparison:** which model class benefits most from aggregation? Intermittent-specific models (Croston, TSB) should see bigger wins.
- **Runtime:** weekly is faster per step (fewer windows needed for the same horizon).

**Narrate:**

- "Series X (intermittent, 70% zeros): daily sMAPE = 1.8, weekly sMAPE = 1.2. Aggregation helps."
- "Series Y (regular, 5% zeros): daily sMAPE = 0.8, weekly sMAPE = 0.9. No benefit; daily is better."

### Section D. Hierarchical planning: item vs item × store (10 min, optional depth)

**Granularity also applies to aggregation levels in hierarchies.**

M5 naturally hierarchies:

```
Store → Department → Category → Item
  ↓         ↓            ↓       ↓
Store_1   FOODS   GROCERY   Item_123
```

You can forecast at any level:

- **Item × Store (most granular):** 30k series in full M5. Fine detail; hard to forecast with limited data.
- **Department × Store (aggregate):** ~100 × 5 = 500 series. More data per series; lose item-level detail.
- **Category × State (coarser):** ~3 × 3 = 9 series. Abundant data; very aggregated.

**Trade-off:**

- **Granular (item × store):** better for store-specific inventory, but each series has less history.
- **Aggregate (category, state):** more stable forecasts, but you need to **disaggregate** to get item-level forecasts. Disaggregation introduces error.

**MMF supports both:**

- Lesson 4.1 forecasts item × store (the 100 M5 series).
- A production system might forecast at store level (faster) and disaggregate proportionally.
- 4.5 Appendix (hierarchical reconciliation, SPEC_HIERARCHICAL_RECONCILIATION) goes deeper.

### Section E. Disaggregation strategies (5 min, optional detail)

If you forecast weekly and need daily forecasts:

1. **Proportional allocation:** divide the weekly forecast across days proportionally to historical daily shares.
   ```
   historical_share[d] = sum(y[d] for d in week) / sum(all y in week)
   daily_forecast[d] = weekly_forecast * historical_share[d]
   ```

2. **Temporal smoothing:** fit a smooth curve (spline) through the weekly forecast and sample daily values. Preserves weekly sum, adds smoothness.

3. **Model-based:** fit a daily-to-weekly reconciliation model (e.g., Nixtla temporal aggregation / ADIDA for intermittent series). More complex but principled.

**For the workshop:** proportional allocation is simplest and suitable for demonstration. Nixtla's IMAPA and ADIDA handle temporal hierarchies and are available in MMF.

## 4. Interactive / visual component

**Recommended: interactive widget** (similar to 3.1 or 4.2):

- **Input sliders:** 
  - `frequency` (Daily / Weekly / Monthly)
  - `series_type` (Regular / Intermittent / Seasonal) — pre-filtered M5 subsets
  - `metric` (sMAPE / MAPE / MAE)

- **Display:**
  - A side-by-side comparison of the same series at daily and weekly granularity.
  - Historical data showing aggregation (e.g., 7 daily bars → 1 weekly bar).
  - Backtest performance (sMAPE) for a few models (Seasonal Naive, LightGBM, Croston, Chronos).
  - A summary: "For intermittent series, weekly is 15% better on average; for regular series, daily is 5% better."

- **Interaction:**
  - Click to toggle between daily, weekly, monthly.
  - Filter by series characteristic.
  - Hover to see exact values.

**Fallback:** static tables and bar charts if the widget isn't feasible.

## 5. Data, setup and runtime

**For the lecture:**

- No compute required. Slides and optional widget use pre-loaded or synthetic data.

**For an optional widget:**

- **Input:** pre-loaded synthetic series (Chronos-style: varied lengths, seasonal patterns, noise) or reference daily/weekly M5 results.
- **Render time:** < 1 s (data is embedded in the notebook or a small cached table).
- **Interaction:** sliders for frequency and series type; charts update in-browser with no server calls.

**Future extensions (not in scope):**

- Hands-on labs would use `mmf.m5.daily_train_100`, resample to weekly, and run forecasts (total ~10 min).
- Reference results (`daily_evaluation`, `weekly_evaluation`) would be pre-computed at setup time.

## 6. Files to create / change

**New files:**

- `labs/Source/en_us/notebooks/M02 - Preparing Many Series/2.5 Appendix - Choosing Forecast Granularity.py` — lecture notebook (Markdown + optional widget, no compute).
- `labs/Source/en_us/notebooks/Includes/_granularity_widget.py` (optional) — interactive widget (self-contained HTML/SVG/JS, like 3.1 / 4.2).

**Modified files:**

- None. Lecture is standalone; no Classroom setup needed.

**Configurations:**

- No change to MMF; existing `forecasting_conf_daily.yaml`, `_weekly.yaml`, `_monthly.yaml` are used as-is.

## 7. Test plan

**Smoke test (any environment):**

- Lecture notebook renders without errors.
- If widget included: JavaScript loads and renders without console errors (test in browser dark/light mode).
- Widget math: verify seasonal length, lags, prediction_length match the YAML configs.

**Widget testing (if included):**

- Synthetic or reference data pre-loaded (no compute at render time).
- Charts re-render correctly when sliders change (frequency, series type, metric).
- No external libraries (HTML/SVG/JS only, like the 3.1 backtest explorer).

## 8. Decisions for the reviewer

1. **Scope: lecture + widget, or lecture-only?**
   - **Confirmed:** 2.5 Appendix (elective) — lecture-only in initial scope. Optional interactive widget (like 3.1, 4.2) if developer time allows.
   - **Reasoning:** the lecture teaches the concepts without hands-on. A widget can let learners explore trade-offs interactively. Any hands-on lab (comparing daily vs weekly runs) is out of scope for now.

2. **Which frequencies to show in the lecture?**
   - **Recommended:** Daily and Weekly (most relevant to M5). Mention Monthly for completeness; skip Hourly (out of scope).
   - **Focus:** temporal (time) aggregation, not cross-sectional (item/store). That's separate (4.5 Appendix).

3. **Interactive widget or static content?**
   - **Recommended:** optional widget (self-contained HTML/SVG/JS, like 3.1 / 4.2). Allows learners to explore daily/weekly/monthly trade-offs interactively. Fallback: static tables and decision framework.
   - **Widget scope:** no external libraries; pre-loaded synthetic or reference data; sliders for granularity / series type / metric.

4. **Hierarchical aggregation (item vs item × store)?**
   - **Confirmed:** mention it (Section D) but don't go deep. See 4.5 Appendix (Hierarchical Reconciliation) for the full treatment.

5. **Disaggregation strategy?**
   - **Included in lecture (Section E):** proportional allocation (simplest method). Reference Nixtla IMAPA / ADIDA (temporal hierarchies) as advanced options for production use.

## 9. Risks and out of scope

**Risks:**

- **Resampling boundaries:** if not done carefully, week boundaries differ across stores or series. Mitigation: use a deterministic, global cutoff (e.g., `F.date_trunc('week', F.col("ds"))`).
- **Sparse weekly data:** resampling a series with very few observations (e.g., 30 days = 4 weeks) results in even sparser weekly data. Foundation models may handle this; statistical models may fail. Mitigation: test and document the breaking point.
- **Exogenous regressors:** if aggregating daily to weekly, what happens to daily regressors (e.g., daily promotions)? Must aggregate them too (sum for sales, mean for prices). Not covered in this lesson; belongs in advanced data prep.

**Out of scope:**

- Hands-on labs comparing daily vs weekly forecasts (belongs in a longer course or advanced exercise).
- Full hierarchical reconciliation (see 4.5 Appendix).
- Distributed resampling optimization (Spark performance tuning).
- Handling daylight-saving time or calendar effects.
- Mixed-frequency forecasting (e.g., daily data but monthly exogenous variables).

## 10. References

- **MMF forecasting configs:** `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/forecasting_conf_*.yaml`
- **Nixtla StatsForecast temporal aggregation:** https://github.com/Nixtla/statsforecast. Models: ADIDA, IMAPA (intermittent demand + temporal hierarchies).
- **Kourentzes et al. on temporal hierarchies:** "Measuring the behaviour of tourism and hospitality firms" and related work on temporal aggregation. (Academic reference; search "Kourentzes temporal aggregation forecasting".)
- **Databricks Spark resample:** `F.date_trunc()`, groupBy + aggregation for time-series resampling.
- **M5 dataset:** M5 Forecasting Competition (Makridakis & Spiliotis, 2020). Walmart retail sales, daily frequency.
