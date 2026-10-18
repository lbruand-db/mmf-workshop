# SPEC — Prediction Intervals and Distributional Forecasting

| | |
|---|---|
| **TODO item** | Theory: point forecasts vs forecast distributions — prediction intervals, quantile (pinball) loss, the newsvendor / service-level trade-off; follows 4.2's bias row (good widget candidate) |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | M04 · 4.3 Appendix - Forecast Distributions and Service Levels |
| **Type / time** | Appendix; optional; ~20 min read + 15 min interactive |
| **Compute** | none (browser) |

---

## 1. Goal and learner outcomes

By the end, participants can:

1. **Explain** the difference between point forecasts and distributional forecasts (full probability distributions).
2. **Interpret** prediction intervals as ranges of plausible outcomes weighted by their probability, and understand confidence levels (e.g., 80%, 95%).
3. **Apply** quantile forecasting (pinball loss) as a method to produce prediction intervals, and understand why it penalizes asymmetrically.
4. **Solve** a simple newsvendor problem: given a forecast with uncertainty, choose an order quantity that balances service level (avoiding stockouts) against holding costs (wasted inventory).
5. **Recognize** when MMF produces prediction intervals (foundation models like Chronos) and when it doesn't (statistical and ML models in the current workshop).

---

## 2. Background — what MMF supports (verified, with source refs)

**MMF's current forecasting approach:**

- **Point forecasts only** in the evaluation loop. All statistical models (StatsForecast: ETS, ARIMA, Croston, etc.) and global ML models (MLForecastLGBM) produce single-value predictions. See `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/abstract_model.py` line 183–199: the metric calculation step computes only `smape`, `mape`, `mae`, `mse`, `rmse` — no quantile or interval metrics.

- **Foundation models produce quantiles internally.** Chronos (ChronosBoltSmall, Chronos2) output full distributional forecasts as quantile arrays, but MMF extracts only the median (0.5 quantile) for evaluation and comparison. See `ChronosPipeline.py` lines 503, 687, 819: median extraction from `forecast[0, quantile_idx, :]`.

- **No native ensembling.** MMF selects a single best model per series based on average backtest metric (Lab 4.1). Combinations are outside MMF's scope and must be computed post-hoc (e.g., in SQL over `evaluation_output`).

**Implication for the workshop:**

Participants see point forecasts throughout the course (1.2 to 4.1). If foundation models run (GPU, instructor-led G1; precomputed Chronos-Bolt in 4.1 otherwise), they see that Chronos produces similar median forecasts to StatsForecast, but with no visibility into Chronos's predicted uncertainty. This appendix fills that gap by:
- Explaining why uncertainty matters (costs, service levels).
- Showing how to compute and interpret intervals from point forecasts (bootstrap, residual-based).
- Introducing quantile forecasting as the method that directly models uncertainty.
- Demonstrating with a self-contained widget.

---

## 3. Proposed content (section-by-section outline)

### Section A: Why point forecasts are not enough

**Lecture**, ~5 min.

- A single number hides the range of plausible outcomes. Two forecasts of "100 units" can have very different reliability.
- Real decisions (order inventory, set staffing levels, plan hedge positions) must trade off under- vs. over-provisioning. Both mistakes have asymmetric costs.
- Forecast accuracy (sMAPE, MAE) measures distance, not insurance: a 10% MAPE forecast is still wrong 10% of the time on average.

**Try this:** Ask participants "If you forecast 100 units sold and you're wrong 15% of the time on average, how many should you stock?" — the answer depends on profit margins and holding costs, which live outside forecasting.

---

### Section B: Prediction intervals and quantiles

**Lecture + demo widget**, ~8 min.

#### B1. Prediction intervals: the idea
- An 80% prediction interval is a range `[lower, upper]` such that the true value falls inside it 80% of the time (in repeated forecasts or histories).
- Wider intervals = more uncertain forecasts. Intervals widen as the horizon grows (more steps ahead = more accumulated error).
- Standard methods: residual-based (assume normality + homoskedasticity), bootstrap (resample residuals), or direct quantile estimation.

**Example:** Forecast is 100 units, 80% interval is [70, 140]. This means: one in five times, actual will be outside this range.

#### B2. Quantiles and the pinball loss
- Instead of a single interval, compute multiple quantiles: 0.1 (10th percentile), 0.5 (median), 0.9 (90th percentile).
- **Pinball loss** = asymmetric penalty for over- vs. under-prediction:
  ```
  L_τ(actual, forecast) = {
    τ × (actual − forecast)    if actual > forecast (underestimate, penalize more for upper quantiles)
    (1−τ) × (forecast − actual)  if actual < forecast (overestimate, penalize more for lower quantiles)
  }
  ```
  - For τ = 0.1 (lower tail): penalize overestimates lightly (we're OK with conservative forecasts), underestimates heavily.
  - For τ = 0.5 (median): symmetric penalty = L2 loss for mean.
  - For τ = 0.9 (upper tail): penalize underestimates lightly, overestimates heavily.

**Why asymmetric?** Because we care about different risks at different tails. When ordering stock, we're more worried about understocking (lost sales) than overstocking (warehouse costs). Pinball loss lets the model learn that trade-off.

#### B3. Foundation models and distributional forecasts
- Chronos models produce quantiles (or samples) internally; MMF keeps only the median (`ChronosPipeline.py`: `np.median(...)` for Chronos-Bolt, the 0.5 quantile for Chronos-2).
- MMF extracts only the 0.5 (median) for evaluation, discarding uncertainty.
- **Available but not shown:** If a participant wants to use Chronos's intervals, they must extract quantile outputs from the MLflow model after scoring and compute quantile metrics (e.g., CRPS—Continuous Ranked Probability Score) separately.

---

### Section C: The newsvendor problem and cost-weighted forecasting

**Lecture + widget**, ~8 min.

The newsvendor (or "newspaper vendor" or "critical fractile") problem is the simplest model linking forecast uncertainty to optimal decisions.

#### C1. The setup
- A vendor buys newspapers at cost *c* per copy, sells at *p* per copy. Demand is random (uncertain).
- Leftover papers are worthless (or recycled for salvage *s < c*).
- How many papers should the vendor buy today (before demand is known)?

#### C2. The cost structure and critical fractile
- **Overstocking cost (holding/waste):** if I buy 100 but only 80 sell, I lose *c* on 20 unsold copies.
- **Understocking cost (lost sales/stockout):** if I buy 80 but 100 want to buy, I lose *(p − c)* profit margin on 20 missed sales.

The **critical fractile** is:
```
F^{-1}( (p - c) / p )
```
- Numerator: profit margin per unit.
- Denominator: selling price (total revenue per unit).
- Ratio: the break-even fraction of demand we must meet to justify buying one more unit.

**Example:** *p* = 2, *c* = 1 (profit margin 50%). Then critical fractile = 0.5. If demand distribution has median above your current stock, buy more. The 50th percentile (median) is the breakeven point.

**Another example:** *p* = 2, *c* = 1.80 (profit margin 10%). Then critical fractile ≈ 0.90. You need to be 90% confident demand ≥ Q to justify buying the next unit—you're very risk-averse because holding costs are high relative to profit.

#### C3. Linking forecast uncertainty to decisions
- If your point forecast is 100 units and you assume demand is normally distributed (point forecast = mean, std dev from residuals), compute the critical fractile quantile and look it up in the normal CDF.
- **If your forecast uncertainty is small (tight interval), you order close to the forecast.** Risk is low.
- **If your forecast uncertainty is large (wide interval), you hedge by ordering a safety stock above the forecast.** Risk is high, and service levels depend on costs.

#### C4. Extension to forecasting metrics
- Standard metrics (sMAPE, MAPE, MAE) reward accuracy but not calibration of intervals.
- **Quantile metrics** (e.g., CRPS) reward intervals that are both accurate (centered on the truth) and sharp (as narrow as possible while capturing truth).
- For a planner, CRPS may be more useful than sMAPE: "Did the model give me an honest estimate of what could happen?"

**Try this:** Given a series with 30% zero days and a forecast interval of [0, 50]:
  1. Which quantile (0.1, 0.5, 0.9) is most useful for ordering lunch inventory at a café?
  2. If profit margin is 40% (sell at $10, cost $6), what is the critical fractile?
  3. If the demand forecast is N(15, 5²), what order quantity do you pick?

**Expected answers:**
  1. 0.9 (we want to avoid stockouts on the high side).
  2. (10−6)/10 = 0.4; so we order at the 40th percentile of demand.
  3. Solve P(Demand ≤ Q) = 0.4 in the CDF: Q = 15 − 1.28×5 ≈ 8.6 (conservative, since profit margin is mediocre and we're risk-averse).

---

## 4. Interactive / visual component

**Widget: Newsvendor Explorer**

A self-contained HTML/SVG/JavaScript widget (no libraries, no network), following the pattern of `_backtest_explorer.py` and `_metric_explorer.py`.

### Parameters (sliders)

1. **Profit margin** (as % of selling price): 10% to 90%, default 50%.
   - Controls the critical fractile (newsvendor problem).
   - Shows how cost structure affects the optimal order quantity.

2. **Forecast: mean** (units): 0 to 100, default 50.
   - Point forecast of demand.

3. **Forecast: std dev** (units): 0.1 to 30, default 5.
   - Spread of plausible outcomes (uncertainty).
   - Controls width of prediction intervals.

4. **Distribution shape** (dropdown): Normal, Lognormal, Poisson.
   - Demonstrates how interval computation varies across distributions.
   - Lognormal is skewed (right-tail risk matters for expensive items).
   - Poisson is discrete (sparse/intermittent demand, like spare parts).

### Panels

**Panel 1: Demand distribution and decision threshold**
- Show the distribution (PDF) as a curve.
- Mark the critical fractile quantile (e.g., 40th percentile for 50% margin) with a vertical line.
- Shade the regions: "understock risk" (demand above quantile) and "overstock risk" (demand below quantile).
- Overlay a vertical line at the point forecast (mean).

**Panel 2: Order quantity and cost breakdown**
- Display the optimal order quantity at the critical fractile.
- Show three scenarios: order 10% below optimal, optimal, 10% above optimal.
- For each, compute and display:
  - Expected holding cost (units unsold × *c*).
  - Expected lost-sales cost (units wanted but not available × (*p − c*)).
  - Total expected cost.
  - **Highlight the optimal as the lowest total cost.**

**Panel 3: Prediction intervals**
- Show 50%, 80%, 95% prediction intervals as shaded bands around the point forecast.
- Update as the user changes mean, std dev, or distribution.

**Panel 4: Robustness check**
- "What if the true demand was different?" — show how well the chosen order quantity performs under 100 alternative demand realizations (same distribution, different random seeds).
- Plot histogram: "In 100 alternative scenarios, your order quantity would cost between $X and $Y on average."
- Link back to the lecture: intervals are only useful if they're calibrated (contain the truth ~50% / ~80% / ~95% of the time).

### Presets (buttons)

- **"Luxury item"** (high margin, tight inventory): 90% margin, mean 50, std dev 5.
- **"Bulk commodity"** (low margin, large variability): 10% margin, mean 100, std dev 40.
- **"Spare parts"** (rare, discrete): Poisson(λ=3), margin 50%.
- **"Seasonal demand"** (right-skewed, rare peaks): Lognormal(mean=20, std dev=15), margin 30%.

### Maths verification

- Critical fractile: Solve P(Demand ≤ Q*) = critical_fractile in the chosen distribution's CDF.
- Expected cost: Integrate over the distribution.
  ```
  E[Cost | Q] = ∫_{-∞}^{Q} c(Q - d) × pdf(d) dd + ∫_{Q}^{∞} (p-c)(d - Q) × pdf(d) dd
  ```
  - First term: holding cost (order Q, sell only d < Q).
  - Second term: lost-sales cost (want d > Q, can only fulfill Q).

**Verification method:** A Node.js prototype will:
1. Sweep all slider combinations (5×5×5×4 = 500 combinations).
2. For each, compute critical fractile analytically (scipy or jstat).
3. Check that the chosen order quantity minimizes expected cost.
4. Verify against finite-sample simulation (10,000 draws).
5. Record max error and pass/fail the sweep.

Results stored in `SPECS/THEORY_PROBABILISTIC_VERIFY.txt` for reviewer.

---

## 5. Data, setup and runtime

**No MMF data required.** The widget runs entirely in the browser with synthetic demand distributions.

### Optional: Real workshop results (Lab 4.1)

If time permits, a follow-up section can show how newsvendor logic applies to the M5 results:

1. **Extract a real series from Lab 4.1** (e.g., a spare part with Croston forecast).
2. **Assume a cost structure** (profit margin 30%, holding cost equals purchase cost).
3. **Compute its critical fractile** and the optimal order quantity.
4. **Show:** If you had used sMAPE to select the best model, vs. if you had used newsvendor cost to select, would you choose the same model?

This section is optional and runs as a static example (no execution required).

---

## 6. Files to create / change

### New files

- `labs/Source/en_us/notebooks/M04/4.3 Appendix - Forecast Distributions and Service Levels.py`
  - Landing notebook, references the widget, theory explanation, and optional real-world example.
  - Includes `Includes/Classroom-Setup-4.3.py` (nothing to set up; uses synthetic data).

- `labs/Source/en_us/notebooks/Includes/_newsvendor_explorer.py`
  - Contains `NEWSVENDOR_EXPLORER_HTML` string (self-contained widget).
  - Companion file (not run as notebook): `SPECS/THEORY_PROBABILISTIC_VERIFY.txt` (verification report).

### Existing files to update

- `SPECS/TODO.md`: Mark item as `[x]` once approved.
- `labs/Source/en_us/notebooks/M04/4.2 Appendix - Choosing a Forecast Metric.py`: Add a brief note (e.g., "See also 4.3 for the cost-of-error perspective").

---

## 7. Test plan

1. **Widget renders** in the Databricks output iframe (Chrome, Firefox, Safari, dark mode).
2. **Sliders and presets update controls** without errors.
3. **Critical fractile is correct** for each slider combination: spot-check 5 scenarios with analytical CDF lookup.
4. **Order quantity minimizes cost** across all 500 combinations (Node.js sweep).
5. **Panel 4 (robustness)** — alternative histories follow the chosen distribution and agree with the widget's intervals (95% CI over 100 runs).
6. **Optional section** runs without error on e2-demo-field-eng (no M5 data dependency; skips if run elsewhere).
7. **Hyperlinks** from 4.2 and to this 4.3 work (if both appendices are present).

---

## 8. Decisions for the reviewer

1. **Should this be a lecture or appendix?**
   - *Recommended: Appendix.* The core workshop (2 hours) doesn't need it; it's for learners who want to go deeper into forecast uncertainty and decision-making.

2. **Which distributions should the widget support?**
   - *Recommended: Normal, Lognormal, Poisson.* Normal is familiar; Lognormal captures right-skew (expensive items); Poisson handles intermittent demand. Student-t could be added later for heavy-tailed uncertainty.

3. **Should we verify maths in the widget's note, or only in a separate Node.js report?**
   - *Recommended: Brief note in the widget* ("Verified against scipy integral to 10⁻⁶"), with full report in SPECS/ for the reviewer's peace of mind.

4. **Is "Optional: Real workshop results" worth the development time?**
   - *Recommended: Include as a static example* (copy code, don't execute). It grounds the theory in the M5 results learners have already seen.

5. **Should prediction intervals be shown in the main Lab 4.1 if foundation models are run?**
   - *Recommended: Not in this spec.* Lab 4.1 compares per-series metrics (already visual); intervals would add complexity. This appendix teaches the concept; a *future* enhancement could extract and display Chronos's quantiles in Lab 5.

---

## 9. Risks and out of scope

### Risks

- **Distribution assumptions**: The widget assumes a chosen distribution matches real demand. In practice, demand may be multimodal (multiple spikes) or have fat tails. *Mitigation:* The optional real example discusses this.
- **Computational cost of large uncertainties**: If std dev becomes very large, the cost integral may become numerically unstable. *Mitigation:* Clamp std dev to reasonable range (< 50% of mean); clamp order quantity to [0, mean + 4×std dev].
- **Learner confusion**: Newsvendor is a new concept for many. *Mitigation:* Three "Try this" exercises with detailed answers in the appendix.

### Out of scope

- **Multi-period inventory models** (dynamic programming, periodic review). This spec covers single-period (one order, one demand realization).
- **Correlation between forecasts and costs** (e.g., seasonal demand with lead times). Keep it simple.
- **Integration of quantile losses into MMF's eval loop.** That requires changes to `abstract_model.py` and is a separate feature request.
- **Ensemble intervals** (combining prediction intervals from multiple models). See Spec 3 (combinations) instead.

---

## 10. References

### Academic

- **Hyndman & Athanasopoulos (2021)**, *Forecasting: Principles and Practice*, 3rd ed.
  - Ch. 5: [Prediction intervals](https://otexts.com/fpp3/prediction-intervals.html)
  - Ch. 11: [Combining forecasts](https://otexts.com/fpp3/combinations.html) (sets up why intervals matter for ensemble combinations)

- **Silver, Pyke & Peterson (1998)**, *Inventory Management and Production Planning and Scheduling*, 3rd ed.
  - Ch. 2: Newsvendor model and critical fractile.

- **Kellogg et al. (2011)**, ["The Value of Uncertain Demand and the Value of the Flexible Capacity," *Manufacturing & Service Operations Management*, 13(2), pp. 1–15.](https://doi.org/10.1287/msom.1100.0322)
  - Quantifies value of forecast accuracy in terms of service levels and costs.

- **Makridakis et al. (2022)**, ["Forecasting with uncertainty: The value of probabilistic forecasts," *European Journal of Operational Research*, 300(1), pp. 180–191.](https://doi.org/10.1016/j.ejor.2021.06.009)
  - M5 Uncertainty competition findings: probabilistic forecasts (intervals) outperform point forecasts on M5.

### Software & tools

- **scikit-learn**: Quantile regression ([`QuantileRegressor`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html))
- **statsmodels**: Quantile ARIMA ([`ARIMA(..., order_by_columns=False)` with `method='powell'` for quantiles](https://www.statsmodels.org/dev/generated/statsmodels.tsa.arima.model.ARIMA.get_forecast.html))
- **sktime**: CRPS and quantile loss metrics ([`QuantileLoss`](https://www.sktime.net/en/stable/api_reference/performance_metrics/))
- **Nixtla MLForecast / StatsForecast**: Support quantile forecasting (e.g., `Chronos` with `num_samples`).
- **MMF** (upstream): Foundation models extract quantiles but don't expose in evaluation output (this appendix discusses why and how to access them post-hoc).

### Datasets

- **M5 Forecasting - Accuracy** (Kaggle): <https://www.kaggle.com/competitions/m5-forecasting-accuracy>
- **M5 Forecasting - Uncertainty** (Kaggle): <https://www.kaggle.com/competitions/m5-forecasting-uncertainty>
  - The Uncertainty track is a direct predecessor to this spec: participants submitted prediction intervals and were scored on quantile metrics (CRPS, quantile loss).
