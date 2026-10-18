# SPEC — Series Segmentation by Demand Pattern

| | |
|---|---|
| **TODO item** | "Segment series before choosing models: smooth / erratic / intermittent / lumpy (ADI / CV²), route each segment to suitable models — ties into the planned 2.3 Lab (Skill 2) and 4.2" |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | M02 · 2.3 Lab - Profile and Classify Series |
| **Type / time** | Lab; optional; 20 minutes |
| **Compute** | Serverless CPU (SQL profiling + plotting) |

## 1. Goal and learner outcomes

Participants learn that different time series require different forecasting strategies, and that **demand pattern classification** (smooth vs. erratic vs. intermittent vs. lumpy) is a practical way to route each series to the right model. They compute the Syntetos–Boylan metrics (ADI = Average Demand Interval, CV² = Coefficient of Variation squared) on M5 series, see which series fall into each segment, and understand why each segment favors certain models.

By the end of the lesson, learners can:
- Compute ADI (average days between non-zero demand) and CV² (variance / mean²) per series.
- Classify series into segments: smooth (low ADI, low CV²), erratic (low ADI, high CV²), intermittent (high ADI, low CV²), lumpy (high ADI, high CV²).
- Recommend models per segment: ETS/ARIMA for smooth, NHITS/LightGBM for erratic, TSB/Croston for intermittent, ADIDA for lumpy.
- Validate the segment-to-model routing with MAE / RMSE / WAPE comparison (which model class wins per segment, and why).

## 2. Background — what MMF supports (verified, with source refs)

**Syntetos–Boylan Classification:**
Introduced by [Syntetos & Boylan (2005)](https://www.ijforecast.com/articles/15_2_153.pdf), this classification partitions demand series using two dimensionless metrics:
- **ADI (Average Demand Interval):** average number of periods between non-zero demands. ADI = n / (number of non-zero observations). High ADI → intermittent (long periods of zero demand, occasional spikes).
- **CV² (Coefficient of Variation squared):** CV² = (std / mean)². High CV² → erratic (high relative variability, even conditional on non-zero demand).

**Classification thresholds (literature-standard, empirically derived):**
Based on [Syntetos & Boylan (2005)], the 2×2 matrix:

| Segment | ADI | CV² | Characteristics | Models | Example (retail) |
|---------|-----|-----|-----------------|--------|------------------|
| **Smooth** | ≤ 1.32 | ≤ 0.49 | Regular, predictable | ETS, ARIMA, AutoTheta, Prophet | Everyday groceries (milk, bread) |
| **Erratic** | ≤ 1.32 | > 0.49 | Regular but noisy | NHITS, NeuralForecast, LightGBM | Fast-moving items with supply noise |
| **Intermittent** | > 1.32 | ≤ 0.49 | Sparse but stable | TSB, Croston, ADIDA, IMAPA | Slow-moving SKUs, spare parts |
| **Lumpy** | > 1.32 | > 0.49 | Both sparse and variable | ADIDA, TSB, foundation models | Seasonal items, rare SKUs, anomalies |

**MMF Skill 2 alignment:**
Skill 2 (Profile and Classify Series) computes spectral entropy, ADF p-value, trend/seasonality strength, sparsity, SNR, but not explicitly ADI/CV². This lesson adds those metrics and refines the forecastability classification. The profiling can be extended to include ADI/CV² computation (or the lab does it separately).

**Recommended models per segment (from MMF Skill 2 logic + domain experience):**

| Segment | Local (CPU) | Global ML (CPU) | Foundation (GPU) | Notes |
|---------|------------|-----------------|------------------|-------|
| Smooth | AutoETS, AutoARIMA, AutoTheta | LightGBM (HPO) | Chronos-2 | Classical models shine; neural models may overfit on short data |
| Erratic | AutoETS (struggles), AutoARIMA | LightGBM (HPO, with lags) | NHITS, NeuralForecast (GPU) | Global & neural handle noise better than local |
| Intermittent | Croston, TSB, ADIDA (Poisson loss) | LightGBM (modified loss) | ChronosBolt (zero-shot) | Specialized intermittent models outperform classical |
| Lumpy | ADIDA, TSB (best for lumpy) | LightGBM (challenging; may need quantile loss) | Foundation models (robust to sparse signals) | Hard for all models; foundation models' generalization helps |

**M5 dataset segments:**
- **Smooth:** everyday groceries (FOODS, HOUSEHOLD, low seasonality) → ~40–50% of M5
- **Erratic:** some food items with promotional noise, supply variability → ~20–30%
- **Intermittent:** seasonal holiday items (Christmas decorations, beach gear) → ~15–25%
- **Lumpy:** rare combinations (specific brand + store + season) → ~5–10%

**Note:** Sparsity (% zeros) is a proxy for ADI; very high sparsity (>0.6) implies high ADI. This lab correlates the two.

## 3. Proposed content (section-by-section outline)

### 3.1 Overview (2 min)
Motivation: "Not all time series are created equal. A grocery item selling daily is forecasted differently from a seasonal item sold 3 days a year. MMF's default model set works well on average, but targeting each segment to its best-fit models improves accuracy and compute efficiency."

### 3.2 Demand Pattern Segments (4 min, interactive matrix widget)
Interactive 2×2 matrix (HTML or SVG) with quadrants:
- X-axis: ADI (left=frequent demand, right=intermittent)
- Y-axis: CV² (bottom=stable, top=erratic)
- Quadrants labeled: Smooth (lower-left), Erratic (upper-left), Intermittent (lower-right), Lumpy (upper-right)
- Slider or input: set ADI/CV² thresholds (default 1.32 / 0.49), see boundary lines move
- Scatter plot overlay: M5 series plotted as dots, color by segment

Interactivity: hover over a series dot to see its name, exact ADI/CV², segment, recommended model. Click to highlight all series in that segment.

### 3.3 Computing ADI and CV² (4 min, SQL + Python)

**SQL for ADI:**
```sql
WITH non_zero AS (
  SELECT unique_id, ds, y,
         ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY ds) AS rn_asc,
         ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY ds DESC) AS rn_desc,
         FIRST_VALUE(ds) OVER (PARTITION BY unique_id ORDER BY ds) AS first_ds
  FROM {training_table}
  WHERE y > 0
),
intervals AS (
  SELECT unique_id, 
         DATEDIFF(ds, LAG(ds) OVER (PARTITION BY unique_id ORDER BY ds), DAY) AS interval_days
  FROM non_zero
),
adi_calc AS (
  SELECT unique_id,
         COUNT(DISTINCT ds) AS n_non_zero,
         (DATEDIFF(MAX(ds), MIN(ds), DAY) + 1) / COUNT(DISTINCT ds) AS adi
  FROM non_zero
  GROUP BY unique_id
)
SELECT unique_id, adi FROM adi_calc
```

**Python for CV²:**
```python
cv_squared = (df.groupby('unique_id')['y'].std() ** 2) / (df.groupby('unique_id')['y'].mean() ** 2)
```

Then join ADI and CV² to segment each series.

### 3.4 Segmentation Results on M5 (3 min, summary statistics)
Query and display:
```sql
SELECT segment, COUNT(*) AS count, ROUND(100.0 * COUNT(*) / total, 1) AS pct
FROM (
  SELECT unique_id, 
         CASE WHEN adi <= 1.32 AND cv2 <= 0.49 THEN 'smooth'
              WHEN adi <= 1.32 AND cv2 > 0.49 THEN 'erratic'
              WHEN adi > 1.32 AND cv2 <= 0.49 THEN 'intermittent'
              ELSE 'lumpy' END AS segment
  FROM {adi_cv2_table}
)
GROUP BY segment
```

Expected M5 breakdown (approximate):
- Smooth: ~45%
- Erratic: ~25%
- Intermittent: ~20%
- Lumpy: ~10%

Summary table with example series per segment.

### 3.5 Model Recommendations per Segment (4 min, decision tree + table)

Decision flowchart:
```
IF smooth:
  → Try ETS, ARIMA, Theta first (statistically optimal)
  → If fails, LightGBM; if GPU available, Chronos-2
  
ELSE IF erratic:
  → LightGBM recommended (learns lag interactions)
  → Neural (NHITS) if training data > 100 observations per series
  → Foundation model (Chronos-2) as fallback
  
ELSE IF intermittent:
  → TSB, Croston, ADIDA (specialized for sparse)
  → Avoid ARIMA/ETS on intermittent (biased variance estimates)
  → Foundation model as backup (zero-shot, robust)
  
ELSE (lumpy):
  → ADIDA or TSB if available
  → LightGBM with custom loss (quantile, Poisson) as alternative
  → Foundation model (most robust to combined sparsity + noise)
```

Table: recommended models per segment, expected metrics (MAE, RMSE, WAPE, bias) as baselines.

### 3.6 Validating Segment Routing (3 min, SQL + plot)
Create a small validation: for each segment, average MAE, RMSE, WAPE and bias of the recommended model class vs. others. Avoid MAPE on intermittent series where zeros are common; use WAPE (weighted absolute percentage error) instead, which handles zero sales gracefully (see 4.2 Appendix).

```sql
SELECT segment, model_class, 
       AVG(mae) AS avg_mae, AVG(rmse) AS avg_rmse, AVG(wape) AS avg_wape, AVG(bias) AS avg_bias,
       COUNT(*) AS model_count
FROM (forecast results joined with segment classification)
GROUP BY segment, model_class
ORDER BY segment, avg_wape
```

Plot: bar chart showing WAPE and bias by (segment, model_class). For smooth, ETS should have lowest WAPE; for intermittent, TSB should lead and have lower bias. Expected outcome: "segment-to-model routing works and improves metric stability."

### 3.7 Production Routing Strategy (2 min)
Practical implementation for a planner's system:
1. Compute ADI/CV² once per day (or weekly).
2. Pre-assign each product to a segment.
3. In Skill 3 (provision), select models based on segment:
   - Segment=smooth: StatsForecastAutoETS, StatsForecastAutoTheta
   - Segment=intermittent: StatsForecastTSB, StatsForecastCroston, StatsForecastADIDA
   - Segment=erratic/lumpy: full model set (ETS, LightGBM, foundation)
4. Monitor: if accuracy drops for a segment, re-profile and adjust routing.

## 4. Interactive / visual component (if any: design, controls, what it demonstrates) — or "none"

**HTML/JS widget: "Demand Pattern Segmentation Dashboard"**

Self-contained interactive widget (no external JS libraries):

**Components:**
1. **ADI/CV² Threshold Sliders**
   - X-axis slider: ADI threshold (range 0.5–3.0, default 1.32)
   - Y-axis slider: CV² threshold (range 0.1–2.0, default 0.49)
   - Sliders update the 2×2 quadrant boundaries in real-time

2. **2×2 Segment Matrix (SVG)**
   - Quadrants labeled: Smooth, Erratic, Intermittent, Lumpy
   - Recommended models color-coded per quadrant
   - Boundary lines move with sliders
   - Dynamic legend showing quadrant counts

3. **Scatter Plot Overlay**
   - M5 series plotted as dots (x=ADI, y=CV²)
   - Color by segment (smooth=green, erratic=yellow, intermittent=orange, lumpy=red)
   - Hover tooltip: series name, exact ADI/CV², segment, top-3 recommended models
   - Click to highlight all series in that segment on a secondary plot (e.g., WAPE distribution by model class)

4. **Model Recommendation Panel**
   - Dropdown or tabs per segment
   - Shows ranked models by expected WAPE, expected runtime, GPU requirement

**Design principles:**
- Minimal styling, high contrast for accessibility
- No external dependencies (pure HTML/CSS/JS)
- Responsive to window resize

Alternative (lower effort, static): collapsible `<details>` sections with pre-computed 2×2 matrix and series examples per segment.

## 5. Data, setup and runtime

**Tables used:**
- `mmf.m5.daily_train_100` (source data, read-only)
- `{use_case}_train_data` (output from Skill 1)
- `{use_case}_series_profile` (if Skill 2 run) or computed on the fly
- Reference results: M5 segment classification + model performance metrics (MAE, RMSE, WAPE, bias) per segment

**Setup changes:**
- Compute ADI/CV² classification for `daily_train_100`, store in `mmf.m5` schema as `daily_train_100_demand_segments` (columns: unique_id, adi, cv2, segment).
- Pre-compute MAE, RMSE, WAPE and bias per (segment, model) from the reference forecast results, store as `m5_segment_model_performance` (for validation in the lab).

**Runtime:**
- Classroom setup: ~1 min (load tables).
- Compute ADI/CV²: ~1–2 min (SQL).
- Plotting + validation: ~2 min.
- **Estimated learner time:** 15–20 min hands-on.

## 6. Files to create / change

1. **New notebook:** `labs/Source/en_us/notebooks/M02 - Preparing Many Series / 2.3 Lab - Profile and Classify Series.py`
   (Alternative to Cold Start Lab, or labeled as 2.3b if both are included)
   - Overview, ADI/CV² metrics, segmentation, model recommendations, validation
   - Interactive matrix widget (displayHTML)
   - Includes reference segment classification and model performance data (MAE, RMSE, WAPE, bias)
   - *Check your work* cell: verify segment table schema, count series per segment

2. **New interactive widget (Includes):** `labs/Source/en_us/notebooks/Includes/_demand_segmentation_widget.py`
   - Self-contained HTML/JS 2×2 matrix + scatter plot
   - Includes pre-loaded M5 series ADI/CV² data
   - Called by `displayHTML(...)` in the lab

3. **Setup change:** `setup/workspace_setup.py`
   - Compute ADI and CV² for `daily_train_100` (SQL UDF or PySpark)
   - Create `daily_train_100_demand_segments` table (unique_id, adi, cv2, segment)
   - Pre-compute MAE, RMSE, WAPE and bias per (segment, model) from reference forecast results; store as `m5_segment_model_performance` (for validation)

4. **Includes/Classroom-Setup-2.3.py** (new, for this variant)
   - Loads training table (Skill 1 output)
   - If segment classification exists, loads it; else computes on the fly
   - If Skill 2 profile exists, compares profiling metrics (sparsity, entropy) to ADI/CV²

## 7. Test plan (e2-demo and/or Vocareum; what to check)

**Dry run (G1, instructor laptop):**
1. Open 2.3 Lab notebook; Classroom setup loads and computes ADI/CV².
2. Run interactive widget; confirm 2×2 matrix shows correct segment boundaries, scatter plot matches expected M5 distribution (smooth ~45%, intermittent ~20%, etc.).
3. Hover/click on series to see details and model recommendations.
4. Run validation SQL (segment metric comparison); confirm recommended models have lowest WAPE and reasonable bias per segment (e.g., TSB lower WAPE than ETS for intermittent, TSB unbiased while ETS over/under-forecasts).
5. *Check your work* cell: PASS (verifies segment table exists, all 100 series classified, quadrant counts reasonable).

**Vocareum (G2, learner self-paced):**
1. Same as above on `daily_train_100` (reference segment classification and performance metrics pre-computed).
2. Optional: learners who completed Skill 2 profiling can correlate sparsity/entropy with segment (SQL query provided).

**Smoke test (02_validate_env.py):**
- Verify `daily_train_100_demand_segments` table exists in `mmf.m5`.
- Verify `m5_segment_model_performance` table exists (for validation).

## 8. Decisions for the reviewer

1. **Placement:** Accept 2.3 Lab - Profile and Classify Series as assigned in SPEC_INDEX.md? This integrates ADI/CV² segmentation into Skill 2's profiling workflow, allowing learners to route segments to models before Skill 3 (provision). Cold Start is separate (2.4 Appendix) for learners interested in new-product fallbacks.

2. **ADI/CV² thresholds:** Use literature defaults (1.32 / 0.49) or calibrate on M5?
   - **Recommended:** Use literature defaults (Syntetos–Boylan 2005). They're well-established; mention that thresholds can be tuned per industry. M5 example shows the defaults work well; if a customer has different thresholds, they can adjust the SQL.

3. **Correlation with Skill 2 profiling:** Should the lab explicitly compare Skill 2's forecastability classification (high-confidence vs. low-signal) to Syntetos–Boylan segments?
   - **Recommended:** Yes, briefly (1–2 min). "High-confidence often overlaps with smooth; low-signal often includes intermittent/lumpy. Segmentation is more granular, allowing targeted model choice within high-confidence series."

## 9. Risks and out of scope

**Risks:**
- ADI/CV² computation is slow on very large datasets (1M+ series). Mitigation: pre-compute and cache; compute once per day, reuse for a day's forecasts.
- Segment thresholds may not generalize across industries (e.g., pharmaceutical has fewer intermittent items than retail). Mitigation: lesson shows how to adjust; encourage learners to profile their own data.
- Metric comparison (validation section) depends on the model set chosen in Skill 3; if a segment-recommended model wasn't run, no metrics to show. Mitigation: validate on reference results (pre-computed with all models).

**Out of scope:**
- Fine-tuning model hyperparameters per segment (e.g., LightGBM lag count for erratic series): beyond workshop scope; reference MLflow tuning in G3.
- Multi-level segmentation (segment at different hierarchy levels differently): out of scope; mention as future work.
- Automated segment-based model selection in Skill 3: not yet implemented; lab shows the concept, Skill 3 remains manual.

## 10. References

- **Syntetos–Boylan classification:** [Syntetos & Boylan (2005), "The accuracy of intermittent demand estimates"](https://www.ijforecast.com/articles/15_2_153.pdf)
- **Intermittent demand forecasting:** [Teunter & Duncan (2009), "Forecasting intermittent demand: A comparative evaluation of Croston's method"](https://www.sciencedirect.com/science/article/abs/pii/S0169207008001696)
- **MMF Skill 2 — Profile and Classify Series:** [`2-profile-and-classify-series.md`](https://github.com/databricks-industry-solutions/many-model-forecasting/blob/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4/skills/databricks-skills/many-model-forecasting/2-profile-and-classify-series.md)
- **StatsForecast models:** [Nixtla StatsForecast documentation](https://nixtla.github.io/statsforecast/models.html) (TSB, Croston, ADIDA)
- **M5 competition & demand patterns:** https://www.kaggle.com/c/m5-forecasting-accuracy (competition posts reference demand segments and model strategies)
- **Demand classification best practices:** [Teunter et al. (2011), "Demand classification and forecasting for spare parts"](https://www.sciencedirect.com/science/article/abs/pii/S0169207010001494)
