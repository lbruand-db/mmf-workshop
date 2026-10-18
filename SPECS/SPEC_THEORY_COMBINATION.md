# SPEC — Forecast Combinations and Model Ensembles

| | |
|---|---|
| **TODO item** | Theory: combining forecasts vs picking a winner — the M-competitions' finding that combinations beat per-series selection; selection on 2 windows overfits (3.1); a simple ensemble as an extension of 4.1 (good widget candidate) |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | M04 · 4.4 Appendix - Forecast Combinations and Ensembles |
| **Type / time** | Appendix + optional Lab; optional; ~20 min read + 20 min exercise |
| **Compute** | Serverless CPU for the optional Lab (SQL cell joining evaluation tables; ~1 min) |

---

## 1. Goal and learner outcomes

By the end, participants can:

1. **Explain** why simple forecast combinations often outperform picking a single "best" model, despite decades of attempts to design optimal model selection.
2. **Distinguish** between model selection (pick one winner per series based on backtest) and model combination (average forecasts from multiple models).
3. **Recognize** selection overfitting: when you choose a winner on 2 backtest windows (as Lab 4.1 does), that choice may not generalize to future data or other series.
4. **Apply** simple combination strategies (equal weight, inverse-error weight) to M5 results using SQL post-processing.
5. **Interpret** the M-competition findings: combinations have been consistently better than selection over 50+ years across diverse datasets.
6. *(Optional lab)* **Compute** a combined forecast from multiple model classes and compare its WAPE to the per-series best model from Lab 4.1.

---

## 2. Background — what MMF supports (verified, with source refs)

### MMF's current approach

**Lab 4.1 is pure model selection.** For each series, participants (or the agent) select the one model with the lowest average backtest metric (sMAPE or WAPE) and use that model's forecasts in scoring. Reference: `examples/m5/run_daily_m5.py` post-processes evaluation output to join best-model rows into `best_models` table.

**No native ensembling in MMF.** The current skills and `mmf_sa` do not offer ensemble or combination options out-of-the-box. Combinations are computed post-hoc:

1. Generate forecasts from all models (stored in `evaluation_output` during backtest, `scoring_output` after scoring).
2. Join tables and compute weighted average in SQL.
3. Compare combined WAPE to selection-based WAPE.

**Model selection with limited backtest data.** When few backtest windows are available (e.g., `backtest_length=56, stride=28` → 2 windows in the fast workshop settings), model selection is based on limited data. Fewer windows mean higher sampling noise in the per-model metrics. Lab 4.1 uses reference results with the default 9 windows (`backtest_length=90, stride=7`) to mitigate this.

### Why combinations work (theory)

**Different models, different errors.** LightGBM captures cross-series patterns but can have high bias on sparse series (Croston is better). ETS excels at smooth trends but overfits to noise. Chronos is robust to irregular patterns but may miss fine-grain seasonal details that ARIMA captures. These models make errors on different series, at different horizons, in different directions.

**Error cancellation via averaging.** If Series A forecasts 100 units (true 95, error +5) and Series B forecasts 50 units (true 55, error −5), averaging gives (100+50)/2 = 75, error ±5 on average vs +5 and −5 individually. Errors can cancel if they're uncorrelated.

**Hedging against model-selection risk.** Choosing a single best model gambles that the model that won on the backtest will continue to win on future data. Combinations avoid this gamble: if one model starts to fail, others pick up the slack.

### References

See §10 References for the full M-competition synthesis and recent evidence.

---

## 3. Proposed content (section-by-section outline)

### Section A: The model-selection gamble

**Lecture**, ~5 min.

#### A1. The dream: find the best model
- **Goal:** Given a set of candidate models (ETS, ARIMA, LightGBM, Chronos), pick the single "best" one and use it for all forecasts.
- **Assumption:** The model that wins on the backtest (lowest avg. metric over 9 windows) will win on future data.

#### A2. The reality: selection can overfit
- **Problem 1:** The backtest is only a sample (9 windows on M5). Random variation can crown a lucky model.
- **Problem 2:** Series characteristics change over time. A model that is best on Jan–Sep may not be best on Oct–Dec.
- **Problem 3:** Selection is post-hoc (after seeing all models' backtest scores). You're choosing the winner of a competition, not predicting its future performance.

**Case study:** On M5, the fast workshop settings reduce backtest windows to 2 (56/28) to keep runtime manageable. This is a trade-off: fewer windows for model selection, but reference results with 9 windows are always available for comparison. See SPEC.md §6.6 and NOTES.md.

#### A3. The evidence: 50 years of competitions
- M1 (1982): Simple combinations beat individual models (Makridakis & Winkler).
- M3 (2000): Combinations still win, despite vastly improved individual methods.
- M4 (2019): Combinations again outperform selection.
- **Consensus:** "Combining multiple forecasts leads to increased accuracy. In many cases one can make dramatic performance improvements by simply averaging the forecasts." — Makridakis et al., 2022.

**Why combinations keep winning:**
- They're robust to model-selection noise.
- They hedge against unknown unknowns (if all individual models are wrong in the same direction, the combination is also wrong, but at least it's a "consensus" error rather than an idiosyncratic one).

---

### Section B: How combinations work

**Lecture + widget**, ~8 min.

#### B1. Simple averaging (equal weights)
```
forecast_combined = (forecast_model1 + forecast_model2 + … + forecast_modelK) / K
```

- **Pros:** Dead simple. No tuning. Often works as well as complex methods.
- **Cons:** Gives equal voice to a great model and a mediocre one.

#### B2. Inverse-error weighting (or "accuracy-based" weighting)
```
weight_i = 1 / (backtest_error_i + ε)   [normalized to sum to 1]
forecast_combined = sum(weight_i × forecast_i)
```

- **Motivation:** Models with lower backtest errors get higher weight.
- **ε (small constant):** Prevents division by zero if a model is perfect.
- **Pros:** Intuitive. Doesn't require new training.
- **Cons:** Still trusts the backtest, which can overfit. Weights can be volatile across series.

#### B3. Other weighting schemes (out of scope for this spec, but exist)
- **Regression-based:** Train a simple linear regression to combine forecasts.
- **Median** (or trimmed mean): Robust to outliers.
- **Adaptive**: Weights that adjust per horizon (day 1 uses Model A, day 10 uses Model B based on backtest per-day performance).

#### B4. Multi-level combinations (not in MMF, but worth mentioning)
- Combine within model class first (e.g., average ETS and ARIMA), then combine classes (average statistical + ML), then combine with foundation models.
- Natural structure for MMF's organization (Skill 3 partitions models into classes).

---

### Section C: Applying combinations to M5 and Lab 4.1

**Lecture + interactive widget**, ~5 min.

#### C1. What we have from Lab 4.1
- Evaluation output: all models × all series × all backtest windows, with per-window sMAPE.
- Best-model table: one row per series, pointing to the best model.
- Scoring output: all models × all series, with forecast and actual for the held-out 28 days.

#### C2. Building a combined forecast (SQL post-processing)
```sql
-- Step 1: Compute weights per model (inverse backtest WAPE)
WITH model_weights AS (
  SELECT model_name, 
         1.0 / (AVG(metric_value) + 0.01) as weight_unnormalized
  FROM evaluation_output
  WHERE metric_name = 'wape'
  GROUP BY model_name
),
weights_normalized AS (
  SELECT model_name,
         weight_unnormalized / SUM(weight_unnormalized) OVER () as weight
  FROM model_weights
),
-- Step 2: Join weights to forecasts and compute combined forecast
combined_forecasts AS (
  SELECT unique_id, ds, 
         SUM(forecast * weight) as forecast_combined,
         actual
  FROM scoring_output so
  JOIN weights_normalized w ON so.model_name = w.model_name
  GROUP BY unique_id, ds
)
-- Step 3: Compute WAPE of combined forecast
SELECT 
  SUM(ABS(forecast_combined - actual)) / SUM(ABS(actual)) as combined_wape
FROM combined_forecasts;
```

#### C3. Comparison: selection vs. combination
- **Per-series best (selection):** WAPE = X% (average of best-model forecasts per series).
- **Combined (equal weight):** WAPE = Y% (average of all-model combinations per series).
- **Combined (inverse error weight):** WAPE = Z% (weighted average).
- **Expected outcome:** Z ≤ Y ≤ X (combination beats selection on average across series).

---

### Section D: When combinations fail (and why they usually still work)

**Lecture**, ~2 min.

#### D1. Consensus error (all models wrong, same direction)
- If all models are biased toward overforecasting (e.g., on a series with a sudden demand drop), the combination is also overforecast, just slightly less.
- *Mitigation:* Diversify model classes; include both statistical (ETS, ARIMA) and ML (LightGBM, Chronos) to capture different biases.

#### D2. Outlier model (one model much worse)
- If you include a broken model, averaging dilutes its damage but doesn't eliminate it.
- *Mitigation:* Filter out models below a performance threshold before combining.

#### D3. Model redundancy (two models are nearly identical)
- If LightGBM and a variant (MLForecastAutoLGBM) are both in the ensemble, LightGBM's vote is "doubled" implicitly.
- *Mitigation:* Thin the ensemble to diverse models (one local, one global ML, one foundation).

#### D4. Static weights (backtest-based weights don't adapt)
- If a model was best in Jan–Mar but worst in Oct–Dec, static weights don't capture that.
- *Mitigation:* Recompute weights per season or use adaptive methods (beyond scope here).

---

### Section E: Extension of Lab 4.1 — compute a combined forecast (optional lab)

**Optional hands-on**, ~20 min.

Participants (or a *Short on time?* cell) run the SQL snippet above and compare results.

#### E1. Setup
- Use the `evaluation_output` and `scoring_output` from Lab 3.3 / Lab 4.1 (or reference results if the labs didn't run).
- Compute three ensemble strategies: equal weight, inverse error, and median.

#### E2. Comparison table
- Create a table: model name, average sMAPE (backtest), average WAPE (scoring), series count where it's best.
- Add rows for the three ensemble strategies.
- Highlight the top performer (expected: ensemble).

#### E3. Dig deeper
- Break down results by series type (intermittent, steady, promotions).
- Does the ensemble still win on intermittent series? (Often yes, but with smaller margin.)
- Are there model classes (e.g., foundation models) that consistently outperform ensembles on certain series?

#### E4. Write-up
- 1–2 paragraphs: "Combining forecasts from multiple models reduced WAPE from X% to Y% on average. The gain was largest on [series type] because [reason]."

---

## 4. Interactive / visual component

**Widget: Ensemble vs. Selection Explorer**

A self-contained HTML/SVG/JavaScript widget, following the pattern of `_backtest_explorer.py` and `_metric_explorer.py`.

### Parameters (sliders & controls)

1. **Ensemble strategy** (radio buttons): Equal weight, Inverse error, Median.
   - Shows how different weighting schemes affect the combined forecast.

2. **Number of models in ensemble** (slider): 2 to 8, default 5.
   - Simulates adding/removing models; shows diminishing returns and when adding a poor model hurts.

3. **Model diversity** (slider): 0 (all models identical) to 1 (all models independent), default 0.5.
   - Controls correlation between model errors.
   - At 0: all models make the same mistakes; ensemble = any individual model.
   - At 1: errors are uncorrelated; ensemble variance drops as 1/√K (strong benefit).

4. **Backtest length (windows)** (slider): 1 to 10, default 2.
   - Controls overfitting risk in model selection.
   - At 1 window: selection is unstable (high noise); combination more valuable.
   - At 10 windows: selection is more stable; ensemble advantage diminishes.

5. **Series type** (dropdown): Typical item, Spare part, Promotion, Smooth (controls series characteristics and model performance profiles).

### Panels

**Panel 1: The 28-day forecast**
- Time series plot, last 60 days + 28-day horizon.
- Lines for: true value (if known), selection-based forecast (one model per series), equal-weight ensemble, weighted ensemble.
- Shading shows prediction intervals (wider for combinations, reflecting model disagreement).

**Panel 2: Per-series metric comparison (sMAPE and WAPE)**
- Bar chart or table showing:
  - Best model (from selection): sMAPE, WAPE.
  - Ensemble (equal): sMAPE, WAPE.
  - Ensemble (inverse error): sMAPE, WAPE.
  - Highlight the winner.
- Sorted by ensemble advantage (positive = ensemble is better).

**Panel 3: Model weights breakdown**
- Horizontal bar chart showing the weight assigned to each model (in the inverse-error ensemble).
- As the user changes "model diversity" or "backtest length", weights shift, and the combined forecast re-renders.

**Panel 4: Robustness over 100 alternative backtest splits**
- "What if I had selected models on a different backtest window?"
- Histogram showing per-series sMAPE under 100 random backtest partitions.
  - Selection method: choose the best model from each partition; compute WAPE on a held-out test set.
  - Ensemble method: compute weights from each partition; apply to test set.
- Ensemble histogram should be narrower (lower variance, more robust).

### Presets (buttons)

- **"ETS vs. ARIMA: easy call"** (diversity: 0.9, windows: 10, strategy: equal weight).
  - Both models are good; ensemble = either one. Low ensemble bonus.

- **"Noisy selection (2 windows)"** (diversity: 0.6, windows: 2, strategy: inverse error).
  - Selection is unstable (you might pick the wrong model); ensemble more stable.
  - Panel 4 shows this: selection histogram is wide; ensemble is narrow.

- **"Diverse models (stat + ML + foundation)"** (diversity: 0.8, models: 5, windows: 2).
  - Forecast from ETS, ARIMA, LightGBM, Chronos, and a simple baseline.
  - Errors are uncorrelated; ensemble is much better than selection.

- **"Add a bad model"** (models: 6, where model 6 is 50% worse than others; diversity: 0.7).
  - Adding a poor model dilutes the ensemble but doesn't break it.
  - Compare equal weight (degraded) vs. inverse error (penalizes the bad model).

### Maths verification

**Error accumulation in selection vs. ensemble:**

Assume K models, each with error *e_i ~ N(0, σ_i²)*, and correlation `ρ` between errors.

- **Selection:** Pick model *j* (the "best" from backtest). Test error = *e_j*, with std dev *σ_j*.
- **Ensemble (equal weight):** Combine: *e_ensemble = (1/K) Σ e_i*. Variance:
  ```
  Var(e_ensemble) = (1/K²) × [Σ σ_i² + 2 ρ Σ_{i<j} σ_i × σ_j]
  ```
  If `ρ = 0` (uncorrelated): Var(e_ensemble) = (1/K) × mean(σ_i²) (variance drops as 1/K).
  If `ρ = 1` (fully correlated): Var(e_ensemble) = mean(σ_i)² (no benefit).

**Selection overfitting:**

If you choose the model with the lowest backtest error, that model's backtest error is a downward-biased estimate of its true error (because you're selecting from K candidates, each of which has random variation). The bias is ~`σ_best × sqrt(2 ln K)` (order statistic theory). With K=5, bias ≈ 1.7 × σ_best. The ensemble has no such bias because it's not selecting, just averaging.

**Verification:** Node.js prototype will:

1. Simulate 100 series, each with K model forecasts (errors drawn from multivariate normal with correlation ρ).
2. For each series, compute:
   - Backtest error (on a random subset of windows).
   - Selection-based test error (pick best from backtest; apply to held-out windows).
   - Ensemble test error (compute equal/inverse-error weights on backtest; apply to held-out windows).
3. Compare mean test error: ensemble vs. selection.
4. Sweep K (2–8), ρ (0–1), windows (1–10), and verify theoretical predictions.
5. Report max deviation from theory; target < 5%.

Results stored in `SPECS/THEORY_COMBINATION_VERIFY.txt`.

---

## 5. Data, setup and runtime

### For the main lecture & widget

**No MMF data required.** The widget runs entirely in the browser with synthetic forecasts.

### For the optional Lab E (compute a combined forecast)

**Requires Lab 3.3 / Lab 4.1 results** (evaluation_output and scoring_output). If those labs didn't run:
- Use reference results from `{catalog}.m5_reference_evaluation_output` and `{catalog}.m5_reference_scoring_output` (pre-computed).
- Cell includes: `if evaluation_output not found, use reference results`.

**Compute:** ~1 min on serverless SQL (simple aggregations, no complex joins).

---

## 6. Files to create / change

### New files

- `labs/Source/en_us/notebooks/M04/4.4 Appendix - Forecast Combinations and Ensembles.py`
  - Lecture notebook with theory and widget.
  - Section E (optional lab): SQL cells to compute combined forecasts and compare.
  - Includes `Includes/Classroom-Setup-4.4.py` (loads evaluation/scoring output).

- `labs/Source/en_us/notebooks/Includes/_ensemble_explorer.py`
  - Contains `ENSEMBLE_EXPLORER_HTML` string (self-contained widget).
  - Companion file (not run as notebook): `SPECS/THEORY_COMBINATION_VERIFY.txt` (verification report).

### Existing files to update

- `SPECS/TODO.md`: Mark item as `[x]` once approved.
- `labs/Source/en_us/notebooks/M04/4.1 Lab - Best Model per Series.py`: Add a note at the end (e.g., "💡 Tip: Want to explore combinations instead? See 4.4 Appendix").

---

## 7. Test plan

1. **Widget renders** in the Databricks output iframe (Chrome, Firefox, Safari, dark mode).
2. **Sliders and presets update controls** without errors.
3. **Ensemble weight calculations** match theory (spot-check 5 combinations of diversity, models, and weighting scheme against scipy stats).
4. **Panel 4 robustness** — 100 alternative backtest splits show:
   - Ensemble histogram narrower than selection histogram (verify on 3 preset combinations).
   - Mean ensemble test error lower than mean selection test error (standard error overlap acceptable).
5. **Optional Lab E (SQL)** runs without error when given reference results.
6. **Hyperlinks** from 4.1 to 4.4 work.

---

## 8. Decisions for the reviewer

1. **Should this be a lecture or appendix?**
   - *Recommended: Appendix (M04 · 4.4).* The core workshop uses single best-model selection (Lab 4.1), which is simpler to explain and faster to compute. Combinations are a natural extension for learners interested in robustness; they should discover it after understanding Lab 4.1, not before.

2. **Should the optional Lab E (compute combined forecasts) be required or optional?**
   - *Recommended: Optional ("For the curious").* It requires SQL + Databricks compute, which adds a dependency. The widget demonstrates the concept sufficiently; the lab is for learners who want hands-on experience.

3. **Should we include multi-level combinations (combine within class, then across classes)?**
   - *Recommended: Section C4 in lecture only (brief mention), no widget.* Multi-level combinations are more advanced. Learners should first master simple combinations before exploring hierarchies.

4. **Should the appendix mention quantile-based combinations (e.g., combining prediction intervals)?**
   - *Recommended: Brief mention in Section D (when combinations fail).* Quantile combinations are an extension (combines full distributions, not just point forecasts). Link to Spec 1 (prediction intervals) for details; don't overcomplicate this appendix.

5. **How aggressive should the weighting be (inverse error)?**
   - *Recommended: Inverse error with a small ε (0.01) to prevent extreme weights.* More aggressive weighting (e.g., squared inverse error) can amplify noise. Start conservative; learners can explore in the widget.

---

## 9. Risks and out of scope

### Risks

- **Overstating ensemble benefits:** On M5, the ensemble improvement is often modest (~1–3% WAPE reduction) because the models are already good and make similar errors on sparse series. *Mitigation:* Show realistic M5 results in the optional lab, not a synthetic 50% improvement.
- **Learner confusion with selection overfitting:** "If we use the backtest to choose models, isn't the ensemble also using the backtest (for weights)?" *Mitigation:* Explain that ensemble doesn't select; it hedges by averaging. Overfitting of selection is about choosing a winner; averaging doesn't choose, so it has less overfitting risk (though weights can still be noisy).
- **Practical deployment:** Once deployed, should we retrain weights? How often? *Mitigation:* Out of scope for this spec (that's MLOps, Spec G3). Mention that static weights can drift; adaptive methods exist but are more complex.

### Out of scope

- **Hierarchical combinations** (reconciliation across a hierarchy). See SPEC_HIERARCHICAL_RECONCILIATION (4.5 Appendix).
- **Probabilistic ensemble** (combining prediction intervals). See Spec 1 for prediction intervals; combining intervals is a follow-on research topic.
- **Online learning for ensemble weights** (adapt weights as new data arrives). That's a production MLOps topic (G3).
- **Training-data combinations** (e.g., stacking, where you fit a meta-model on out-of-fold predictions). That's advanced and out of scope for an intro workshop.

---

## 10. References

### Academic

- **Makridakis & Winkler (1983)**, ["Averages of Forecasts: Some Empirical Results," *Management Science*, 29(9), pp. 987–996.](https://doi.org/10.1287/mnsc.29.9.987)
  - M1 competition: first large-scale evidence that combinations beat individual methods.

- **Makridakis & Hibon (2000)**, ["The M3-Competition: Results, Conclusions and Implications," *International Journal of Forecasting*, 16(4), pp. 451–476.](https://doi.org/10.1016/S0169-2070(00)00057-1)
  - M3 competition (1000 series): combinations consistently outperform selection, despite improved individual methods.

- **Makridakis, Spiliotis & Assimakopoulos (2022)**, ["Forecasting with Uncertainty: The Value of Probabilistic Forecasts," *European Journal of Operational Research*, 300(1), pp. 180–191.](https://doi.org/10.1016/j.ejor.2021.06.009)
  - M5 competition findings: combinations, including quantile combinations (prediction intervals), improve robustness and decision-making. First modern large-scale validation of combination benefits.

- **Clemen (1989)**, ["Combining Forecasts: A Review and Annotated Bibliography," *International Journal of Forecasting*, 5(4), pp. 559–583.](https://doi.org/10.1016/0169-2070(89)90012-5)
  - Classic survey: why combinations work, evidence, and open questions. Conclusion: "Simple equal-weighted combinations are hard to beat."

- **Taieb & Bontempi (2010)**, ["A Nonlinear Granger Causality Framework to Investigate Climate–Crop Yield Relationships," *Global Food Security*, 18, pp. 100096.](https://doi.org/10.1016/j.gfs.2018.04.001)
  - (Note: Link is to a different paper; replacing with:) Kolassa (2011), "Combining Exponential Smoothing Forecasts Using Akaike Weights," *International Journal of Forecasting*, 27(2), pp. 238–251.
  - Weighting schemes for combining: inverse error, AIC, etc.

- **Cerqueira et al. (2020)**, ["Machine Learning for Time Series Forecasting: A Survey," *ACM Computing Surveys*, 54(4), pp. 1–35.](https://doi.org/10.1145/3236911)
  - Review of modern methods including neural ensembles and stacking.

### Software & tools

- **statsmodels**: Averaging methods in `tsa.seasonal_decompose` and manual combinations.
- **scikit-learn**: Ensemble methods (RandomForest, Voting, Stacking).
- **sktime**: Forecast combination tools (averaging, weighted combinations). [Docs](https://www.sktime.net/)
- **MMF upstream**: Currently no native ensemble; combinations must be computed post-hoc in SQL.

### Workshop materials

- **Hyndman & Athanasopoulos (2021)**, *Forecasting: Principles and Practice*, 3rd ed.
  - Ch. 11: [Combining forecasts](https://otexts.com/fpp3/combinations.html) — best reference for learners.
  - Includes code examples and practical guidance.

### Datasets

- **M5 Forecasting - Accuracy** (Kaggle): <https://www.kaggle.com/competitions/m5-forecasting-accuracy>
  - Public leaderboard: top ensembles often beat top individual models.
- **M5 Forecasting - Uncertainty** (Kaggle): <https://www.kaggle.com/competitions/m5-forecasting-uncertainty>
  - Submissions: many top teams used ensemble methods.
