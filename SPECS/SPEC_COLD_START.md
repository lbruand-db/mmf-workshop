# SPEC — Cold Start and Short Histories

| | |
|---|---|
| **TODO item** | "Cold start and short histories: which series MMF's data-quality checks drop (too short, too many gaps) and the fallbacks (category-level forecast, global or foundation models)" |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | M02 · 2.4 Appendix - New and Short Series |
| **Type / time** | Appendix; optional follow-up to Skill 2 profiling; 15 minutes |
| **Compute** | Serverless CPU (profiling, SQL fallback generation) |

## 1. Goal and learner outcomes

Participants understand which series are too short or sparse for MMF's forecasting models, why they fail, and how to apply practical fallbacks. They see the data quality checks that drop series, learn to recognize patterns (insufficient historical data, too many gaps, excessive zeros), and choose a fallback strategy: aggregate to a higher level, use a simpler model (baseline), or mark for manual review.

By the end of the lesson, learners can:
- Run MMF's data quality checks and interpret which series are flagged and why.
- Recognize cold-start scenarios: new products with <2 weeks of history, intermittent demand with >50% zeros, series shorter than the forecast horizon.
- Apply a fallback strategy: aggregate to category level (category-level forecast), use SeasonalNaive at the product level, or route to a separate low-signal model job.
- Validate the choice with a "forecast score" dashboard (fallback MAE / WAPE vs. baseline).

## 2. Background — what MMF supports (verified, with source refs)

**Data Quality Checks in MMF:**
MMF's `data_quality_checks.py` ([upstream source](https://github.com/databricks-industry-solutions/many-model-forecasting/blob/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4/mmf_sa/data_quality_checks.py)) runs **mandatory** and **optional** validation on each series. Checks are applied during Skill 1 (prep) if `data_quality_check=True` in the config; Skill 2 (profiling) also classifies series by forecastability.

**Mandatory checks (always run, regardless of config):**
- `backtest_length >= prediction_length`: backtest window must be ≥ forecast horizon.
- External regressors: no NULLs in dynamic features, resampling disabled if external regressors present.

**Optional checks (if `data_quality_check=True`):**
- `training_period_length`: minimum `train_predict_ratio * prediction_length` positive (>0) training points before backtest start date. Default ratio: 1.0, so for 28-day horizon, need ≥28 training days.
- `missing_entries`: if `resample=True`, resample missing dates and check `missing_ratio <= missing_data_threshold` (default: 0.2, i.e., ≤20% gaps allowed).
- `negative_entries`: `negative_ratio <= negative_data_threshold` (default: 0.2, i.e., ≤20% negative values).

**Workshop observation (2026-10-15 test run):**
On `daily_train_100` with `backtest_length=90, stride=7, prediction_length=28`: 
- Initial series: 100
- After data quality checks: 99 (1 series dropped)
- Removal reason: insufficient training data (series too short or started mid-month)

This single dropped series is a good teaching opportunity: show which one, why, and how to handle it.

**Profiling-based classification (Skill 2):**
Beyond hard data quality failures, Skill 2 classifies each series as "high_confidence" or "low_signal" based on:
- `spectral_entropy < 0.8` (noise level)
- `series_length >= 2 * prediction_length` (length criterion)
- `sparsity < 0.5` (<50% zeros)
- `snr > 0.1` (signal-to-noise ratio)

Series failing these thresholds are marked low_signal and can be routed to fallback strategies (Strategy A: keep all, B: exclude + fallback rule, C: exclude + separate job).

**Fallback strategies:**
1. **Aggregate to parent level** (category, dept, store, region): use category-level forecast as proxy for product-level. Trades granularity for stability.
2. **SeasonalNaive or Naive baseline** on the product: simple rule, no training. Appropriate for very short series (<30 days).
3. **Foundation model only** (Chronos-Bolt): zero-shot, no training; works on very short data; slower than statistical baselines.
4. **Zero forecast**: for series with >80% zeros (seasonal spikes, intermittent demand) where a value>0 is unlikely in the forecast window.
5. **Category-level + adjustment**: forecast category, then distribute using historical proportions (synthetic item-level forecast).

**Test data in the workshop:**
M5 `daily_train_100` includes examples of each:
- **Short history:** some series start mid-dataset, <90 days available before backtest.
- **Intermittent:** seasonal items with high sparsity (e.g., holiday-only products).
- **Gaps:** days with zero sales due to store closures or data collection issues.

## 3. Proposed content (section-by-section outline)

### 3.1 Overview (2 min)
Real-world cold start: new product launched at a store (0 history), existing product with 2 weeks of data, seasonal item with only 3 peak days per year. Standard forecasting struggles; need pragmatic fallbacks. This lesson shows which series fail, why, and how to rescue them.

### 3.2 MMF's Data Quality Checks (4 min, interactive SQL)
Walk through the checks that drop series:
- **Training period check:** series must have ≥ `train_predict_ratio * prediction_length` positive observations before the backtest window.
  - Pseudo-code: `SELECT COUNT(*) FROM series WHERE y > 0 AND ds < backtest_start_date`
  - Failures: series < 28 observations (for 28-day horizon with ratio=1.0), or first observation >90 days before end
- **Missing data check:** if resample enabled, gap ratio must be ≤ 20%.
  - What counts: gaps in the date sequence (e.g., store closed on Sundays)
- **Negative value check:** ≤20% negative entries (handles returns, adjustments).
- **External regressor NULLs:** checked per series, can cause drops if regressors missing for specific items.

**M5 observation:** Run MMF's checks on `daily_train_100` with and without `data_quality_check=True` to show which series pass/fail.

Interactive: data quality report widget showing:
| Series | Reason | Training days | Gaps | Negatives | Action |
|--------|--------|---------------|------|-----------|--------|
| FOODS_3_090_CA_1 | insufficient training | 20 | 0% | 0% | DROP |
| FOODS_1_001_CA_1 | OK | 1460 | 1% | 0% | KEEP |

### 3.3 Profiling-Based Forecastability (3 min)
Skill 2's profile scores each series:
- High-confidence: stable, enough data, low noise → standard MMF models
- Low-signal: noisy, short, sparse → fallback or separate job

Show the profiling table columns:
- `spectral_entropy`: 0=perfect signal, 1=pure noise. High entropy (>0.8) → hard to forecast.
- `sparsity`: fraction of zeros. >0.5 → intermittent demand, need special models.
- `snr`: signal-to-noise ratio. <0.1 → too noisy.
- `series_length`: compared to `2 * prediction_length` threshold.

Example: M5 intermittent item (high sparsity, low SNR, passes length check) → low-signal despite having enough days, because the signal is buried in noise.

### 3.4 Recognizing Cold-Start Patterns (4 min, visual guide)
Common patterns and how to detect them via SQL:

| Pattern | Detection | MMF outcome | Fallback |
|---------|-----------|------------|----------|
| **New product** | `COUNT(ds) < 30` or `MIN(ds) > 90 days ago` | Training period FAIL | Use category forecast or SeasonalNaive |
| **Intermittent** | `COUNT(y>0) / COUNT(*) < 0.2` (sparsity > 0.8) | Low-signal classification | TSB/Croston if available, else SeasonalNaive or Zero |
| **Highly seasonal** | `high spectral_entropy`, `seasonality_strength > 0.7` | May be high-signal IF enough data | ETS or foundation models; mark for review if <60 days |
| **Gaps due to closures** | `MAX(gap_between_dates) >> expected frequency` | Missing data FAIL (if resample) | Treat as sparse; adjust threshold or disable resample |
| **Returns/adjustments** | `negative_ratio > 0.2` | Negative value FAIL | Filter negatives or use loss function that tolerates them (e.g., WAPE) |

### 3.5 Fallback Strategy Selection (3 min, SQL + decision tree)
For each cold-start pattern, a recommended fallback:

```
IF insufficient training data:
  IF parent (category) level available:
    → Use category-level forecast (all items in category get the same forecast)
  ELSE IF series sparsity > 0.5:
    → SeasonalNaive (repeat last seasonal cycle)
  ELSE:
    → Naive (carry forward last value) or Zero if mostly zero
```

Query to find cold-start candidates:
```sql
SELECT unique_id, COUNT(DISTINCT ds) AS days_available, 
       ROUND(1.0 * SUM(CASE WHEN y=0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS sparsity
FROM {training_table}
GROUP BY unique_id
HAVING days_available < 60 OR sparsity > 0.5
```

### 3.6 Implementing Fallbacks (3 min, SQL demo)
Example SQL for each fallback:

**Aggregate to category:**
```sql
CREATE TABLE {use_case}_forecast_fallback_category AS
SELECT ds, category_id, SUM(y_forecast) AS y_forecast
FROM {forecast_table}
GROUP BY ds, category_id
```

**SeasonalNaive fallback (for excluded low-signal series):**
```sql
CREATE TABLE {use_case}_forecast_fallback_naive AS
WITH last_season AS (
  SELECT unique_id, ds, y,
         ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY ds DESC) AS rn
  FROM {training_table}
  WHERE unique_id IN (SELECT id FROM low_signal_series)
)
SELECT unique_id, 
       ARRAY(SELECT y FROM last_season WHERE rn <= {prediction_length} ORDER BY rn)
FROM last_season
```

**Zero forecast:**
```sql
SELECT unique_id, 
       ARRAY_REPEAT(0.0, {prediction_length}) AS y_forecast
FROM cold_start_series
```

Emphasize: choose the fallback that matches the use case. Inventory planning (stock needed): aggregate to category or SeasonalNaive. Spare parts (intermittent): Zero or TSB model. Revenue: category aggregate + proportional distribution.

### 3.7 Validation and Business Use (2 min)
Post-fallback, validate the forecast quality:
- **MAE / WAPE on recent history:** if the series has >30 days history, backtest the fallback (e.g., SeasonalNaive) on the last 14 days to estimate its accuracy (use WAPE instead of sMAPE on series with high zero proportion — see 4.2 Appendix).
- **Sanity checks:** Is the aggregate in the right ballpark? Does SeasonalNaive forecast match last year's season?
- **Human review:** Flag very cold starts (0–7 days history) for manual approval; automated fallback is imperfect.

Dashboard: cold-start series with their fallback, confidence score (1=manual review, 0.5=reasonable, 1.0=high confidence). Show category aggregate alongside item fallback.

## 4. Interactive / visual component (if any: design, controls, what it demonstrates) — or "none"

**HTML/JS widget: "Cold-Start Detector and Fallback Recommender"**

Self-contained notebook cell:
- Input: data table (CSV or JSON) with columns `unique_id`, `ds`, `y`
- Auto-detect: series length, sparsity, gaps, negative ratio per series
- Output: table with each series' risk level (🟢 GREEN high-confidence, 🟡 YELLOW borderline, 🔴 RED cold-start), recommended fallback, and action buttons
- Visualization: bar chart showing distribution of series by risk level; hover for details

Alternatively (lower effort): collapsible `<details>` blocks with static examples and SQL snippets.

## 5. Data, setup and runtime

**Tables used:**
- `mmf.m5.daily_train_100` (source data, read-only)
- `mmf.m5_static_features` (category, dept info for aggregation)
- `{use_case}_train_data` (output from Skill 1)
- `{use_case}_series_profile` (output from Skill 2, if run)
- `{use_case}_pipeline_config` (strategy chosen in Skill 2, if run)

**Setup changes:**
- Add reference data: a pre-computed cold-start series subset from `daily_train_100` (e.g., 5–10 series with <30 days history or >0.5 sparsity), staged in `mmf.m5_reference` as `reference_cold_start_examples`. Used in *Check your work*.

**Runtime:**
- Classroom setup: ~1 min (load tables, compute cold-start statistics).
- Fallback SQL: ~1–2 min (generate fallback forecasts on 100 series).
- Validation: ~1 min (backtest fallback, plot).
- **Estimated learner time:** 15 min hands-on.

## 6. Files to create / change

1. **New notebook:** `labs/Source/en_us/notebooks/M02 - Preparing Many Series / 2.4 Appendix - New and Short Series.py`
   - Overview, cold-start detection, fallback strategies, SQL examples, validation
   - Includes reference cold-start series and pre-computed fallback outputs
   - *Check your work* cell: count fallback forecasts, verify counts match cold-start series

2. **New interactive widget (Includes):** `labs/Source/en_us/notebooks/Includes/_cold_start_detector.py`
   - Self-contained HTML/JS widget to detect cold-start patterns
   - Called by `displayHTML(...)` in the lab

3. **Setup change:** `setup/workspace_setup.py`
   - Add step to identify and stage cold-start series from `daily_train_100` as reference examples in `mmf.m5_reference`
   - SQL: filter `daily_train_100` for series with `COUNT(ds) < 60` or sparsity > 0.5, store in `reference_cold_start_examples`

4. **Includes/Classroom-Setup-2.3.py** (new)
   - Loads training data from Skill 1 (via `_common`)
   - If Skill 2 profiling was run, loads profile; else computes sparsity/length stats on the fly

## 7. Test plan (e2-demo and/or Vocareum; what to check)

**Dry run (G1, instructor laptop):**
1. Open 2.4 Appendix notebook; Classroom setup loads data and computes cold-start statistics.
2. Run cold-start detector widget; confirm it flags low-signal series correctly (compare to Skill 2 profile if available).
3. Run fallback SQL; verify fallback table row counts match cold-start series count.
4. Run validation SQL; spot-check a few fallback forecasts (e.g., SeasonalNaive should be non-zero if sparsity < 1.0).
5. *Check your work* cell: PASS (confirms fallback table exists, row count correct, columns present).

**Vocareum (G2, learner self-paced):**
1. Same as above on `daily_train_100` (reference cold-start examples pre-staged).
2. Optional: learners run Skill 2 profiling and compare profile results to the detector widget.

**Smoke test (02_validate_env.py):**
- Verify `reference_cold_start_examples` table exists in `mmf.m5_reference`.
- Verify Skill 1 or Skill 2 outputs exist (training table or profile table).

## 8. Decisions for the reviewer

1. **Placement:** Accept 2.4 Appendix - New and Short Series as assigned in SPEC_INDEX.md? This positions cold start as an optional follow-up to 2.3 Lab (Segmentation), for learners interested in fallback strategies for new/sparse products. The 2-hour core is full; cold start is not required.

2. **Fallback scope:** Scope to top 3 fallback strategies (aggregate to category, SeasonalNaive, Zero)? Or include Croston/TSB/foundation models?
   - **Recommended:** Top 3 (covers 90% of real-world cold starts). Mention specialized models (Croston, TSB, foundation) in "Further reading" for advanced learners; they're better handled in a dedicated low-signal job (Skill 2 Strategy C).

## 9. Risks and out of scope

**Risks:**
- Learners apply an inappropriate fallback (e.g., SeasonalNaive to a completely new product with 0 history → forecasts nonsense). Mitigation: validation section emphasizes human review for extreme cases; *Check your work* includes a sanity check (forecasts not all NaN, not all negative).
- Data quality check thresholds (`train_predict_ratio=1.0`, `missing_data_threshold=0.2`) may be too strict or loose for the learner's use case. Mitigation: lesson shows how to adjust thresholds in the config; encourage learners to validate on their own data.
- Aggregating to category loses item-level granularity; planner might not accept it. Mitigation: discuss trade-offs; mention that this is a temporary placeholder until more data arrives.

**Out of scope:**
- Online learning (forecast improves as data arrives): not in MMF scope; reference MLOps module for retraining cadence.
- Probabilistic forecasts for cold start (prediction intervals): beyond 2-hour workshop scope; mention confidence levels as a future topic.
- Automated fallback selection (model auto-selection based on series characteristics): Skill 2 already does this; this lab is the manual follow-up for edge cases.

## 10. References

- **MMF data quality checks:** [`mmf_sa/data_quality_checks.py`](https://github.com/databricks-industry-solutions/many-model-forecasting/blob/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4/mmf_sa/data_quality_checks.py) (source; see `DataQualityThresholds`, `_check_training_period_length`, `_check_missing_entries`)
- **MMF Skill 2 — Profile and Classify:** [`2-profile-and-classify-series.md`](https://github.com/databricks-industry-solutions/many-model-forecasting/blob/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4/skills/databricks-skills/many-model-forecasting/2-profile-and-classify-series.md) (forecastability classification logic)
- **StatsForecast baseline models:** [Nixtla StatsForecast docs](https://nixtla.github.io/statsforecast/models.html) (SeasonalNaive, Naive, Zero)
- **Intermittent demand forecasting:** Croston, ADIDA, TSB models in [StatsForecast](https://nixtla.github.io/statsforecast/models.html)
- **M5 dataset:** https://www.kaggle.com/c/m5-forecasting-accuracy (note cold-start challenge in the competition)
- **Cold start in recommender systems (analogy):** https://en.wikipedia.org/wiki/Cold_start_problem (adapted for forecasting)
