# SPEC — Multi-Step Forecasting Strategies

| | |
|---|---|
| **TODO item** | Theory: multi-step strategies — recursive vs direct forecasting, error growth over the 28-day horizon (MMF's LightGBM is recursive) (good widget candidate) |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | M03 · 3.5 Appendix - Multi-Step Forecasting and Error Growth |
| **Type / time** | Lecture-style appendix + widget; optional; ~20 min read + 15 min interactive |
| **Compute** | none (browser) |

---

## 1. Goal and learner outcomes

By the end, participants can:

1. **Explain** the two main multi-step forecasting strategies: recursive (one-step-ahead, iterate) vs. direct (train separate models per horizon).
2. **Recognize** error accumulation: in recursive forecasting, mistakes on day 1 propagate to days 2–28, degrading performance as the horizon grows.
3. **Assess trade-offs**: recursive is simpler and often wins on short horizons; direct is more complex but avoids error compounding on long horizons.
4. **Identify** which strategy MMF uses for each model class (verified from source).
5. **Anticipate** forecast accuracy decay: when presenting results (4.1 Lab), note that model performance for day 28 is typically worse than for day 1.

---

## 2. Background — what MMF supports (verified, with source refs)

### MMF's implementation

**Statistical models (StatsForecast):**

All local StatsForecast models (ETS, ARIMA, Theta, Croston, etc.) use **iterative equations** from a single fitted model to produce multi-step forecasts. For example, ARIMA fitted to the history is applied repeatedly to project h steps ahead; ETS uses its state-space equations; Croston projects its demand and intermittency processes. This is neither "recursive" (feeding predictions back as lag features) nor "direct" in the Taieb sense (training separate models per horizon). Instead, each model class has built-in equations for multi-step projection. These equations are themselves recursive in their own state: the h-step forecast is built from the (h−1)-step forecast, so errors in the estimated level, trend and seasonality carry forward and accuracy also degrades with the horizon (prediction intervals widen accordingly). What differs from MLForecast's recursion is that no *learned* lag features are fed with predictions — the propagation follows the model's own structure, which for simple models (Seasonal Naive, flat Croston/TSB forecasts) gives a repeating or flat path. Reference: StatsForecast's `forecast()` method returns arrays of length `prediction_length` in one pass.

**Global ML model (MLForecastLGBM):**

Uses **recursive multi-step forecasting**. The LightGBM model is trained on lagged features (lags: [1, 7, 14, 28] per `models_conf.yaml` line 331) to predict one step ahead. At scoring time, predictions are made iteratively:

1. Fit on historical data up to date *t*.
2. Predict day *t+1* using lags [y_t, y_{t-6}, y_{t-13}, y_{t-27}].
3. Use the predicted *ŷ_{t+1}* as an input for the next step.
4. Predict day *t+2* using lags [ŷ_{t+1}, y_t, y_{t-6}, y_{t-13}].
5. Repeat through day *t+28*.

Reference: `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/mlforecast/MLForecastPipeline.py` lines 286–312 (the `_model_predict` method iterates using `mlforecast.MLForecast.predict` with updated `new_df` containing prior predictions). MLForecast's default is recursive; direct is an explicit option but is not configured in MMF's baseline.

**Foundation models (Chronos, TimesFM):**

Produce the full forecasting horizon in a single pass (direct-like), but unlike traditional direct methods, they use a neural architecture that conditions on the entire history. Some also output quantiles (distributional) rather than point estimates. Reference: `ChronosPipeline.py` lines 500–570 call `pipeline.predict()` once and extract all `prediction_length` steps from a single invocation.

### Implication for the workshop

- **Lab 3.3 comparison**: StatsForecast (iterative equations) vs. MLForecastLGBM (recursive with lag features) produce forecasts via different mechanisms. On M5 (28-day horizon), the performance gap reflects these strategies' trade-offs: recursive feeds prediction errors back as features (amplifying or damping depending on lag structure); iterative models project via their own equations (natural uncertainty growth, wider intervals).
- **Accuracy by day (Lab 4.1 evaluation)**: If learners inspect the evaluation output per day, they can see that day 1 accuracy is often better than day 28 for MLForecastLGBM (error compounding from fed-back predictions). Statistical models degrade with the horizon too; how fast, compared with LightGBM, is an empirical question to measure on the reference results, not something theory settles.
- **Why LightGBM is here**: Despite recursive error accumulation, LightGBM is valuable because it can learn complex cross-series patterns (which lags matter, when to use recent vs. seasonal) and often wins on the M5 benchmark. The model class comparison (Lab 4.1) lets learners see this trade-off empirically.

---

## 3. Proposed content (section-by-section outline)

### Section A: The problem — predicting 28 days ahead

**Lecture**, ~4 min.

- **Context:** M5 horizon is 28 days. We need a forecast for every day from *t+1* to *t+28*.
- **Naive approach:** Train a single model `f` to output all 28 values at once, given history. ✓ Simple, ✗ How?
- **Two strategies emerged historically:**
  1. **Recursive**: Use `f` to predict 1 step, feed it back, repeat. ✓ Reuses one model, ✗ Errors compound.
  2. **Direct**: Train separate models `f_1, f_2, …, f_{28}`, one per day ahead. ✓ No compounding, ✗ Complex, lots of models.

**Motivation:** Both approaches are used across industry and academia. Different datasets and problems favor different strategies. Participants should understand why both exist.

---

### Section B: Recursive forecasting (also called "iterated" or "one-step-ahead")

**Lecture + widget**, ~7 min.

#### B1. How it works
```
Day t+1: ŷ_{t+1} = f(y_1, y_2, …, y_t)
Day t+2: ŷ_{t+2} = f(y_1, y_2, …, y_t, ŷ_{t+1})
Day t+3: ŷ_{t+3} = f(y_1, y_2, …, y_t, ŷ_{t+1}, ŷ_{t+2})
…
Day t+h: ŷ_{t+h} = f(y_1, y_2, …, y_t, ŷ_{t+1}, …, ŷ_{t+h-1})
```

The model is a **single function `f`**, typically a regression model trained on past history (e.g., ARIMA, AR with lags, LightGBM).

#### B2. Example: AR(28) forecasting with LightGBM
- Features: `y_{t-1}, y_{t-7}, y_{t-14}, y_{t-28}` (last value, last week, last two weeks, last month).
- Train on all past (`t=1` to `t=T`), predicting `y_{t+1}` from lagged features.
- At scoring: use observed history + predicted future to build lags, iterate 28 times.

#### B3. Trade-offs

**Advantages:**
- Single model: fewer parameters to train, simpler to interpret.
- Often wins on short horizons (1–7 days), where error hasn't compounded much.
- Natural fit for ARIMA, exponential smoothing, and lag-based ML models.

**Disadvantages:**
- **Error accumulation / horizon-specific error growth**: Mistakes on day 1 become inputs to day 2, amplifying errors down the line.
- **Covariate shift**: At training time, lags are *observed* (true past values); at scoring time, lags are *predicted* (future estimates). This mismatch can confuse the model.
- **No horizon-specific adaptation**: the same model must work for both nearby and distant predictions.

#### B4. Error accumulation — visualization in widget
- Start with a clean forecast on day 1 (error = 0).
- Introduce a small error on day 1 (e.g., +5% overestimate).
- Visualize how that error propagates and compounds through day 28.
- **Key insight:** If the model has a persistence (e.g., ARIMA with a unit root), the error doesn't fade; if the model dampens (e.g., exponential smoothing), the error may be corrected. But lag-based models (LightGBM) can learn complex persistence patterns, leading to either amplification or damping depending on the series.

---

### Section C: True direct forecasting (training separate models per horizon)

**Lecture + widget**, ~7 min.

#### C1. How it works (definition from Taieb et al.)
```
Model f_1: ŷ_{t+1} = f_1(y_1, y_2, …, y_t)       [trained on all data to predict h=1]
Model f_2: ŷ_{t+2} = f_2(y_1, y_2, …, y_t)       [trained on all data to predict h=2]
…
Model f_h: ŷ_{t+h} = f_h(y_1, y_2, …, y_t)       [trained on all data to predict h=h]
```

**Key difference from recursive:** Each model is trained separately, using only the observed history (no predicted future as features). No model feeds its output back to another model.

#### C2. Example: Direct LightGBM on M5 (not used in MMF, but a thought experiment)
- For each horizon *k ∈ {1, 2, …, 28}*, train a separate LightGBM.
- Training data for `f_k`: create labels that are exactly *k* steps ahead (y_{t+k}), using history (y_1, …, y_t) as features.
- Features for `f_k`: same lags `[y_{t-1}, y_{t-7}, y_{t-14}, y_{t-28}]`, but the labels are horizon-specific.
- At scoring: call each model once with the observed history; collect results.
- **Result:** No prediction error feeds forward; each forecast is independent.

#### C3. Trade-offs

**Advantages:**
- **No error accumulation**: Errors on day 1 don't propagate to day 2, 3, etc.
- **Horizon-specific learning**: `f_k` can learn patterns specific to day *k* (e.g., day 7 behaves differently than day 14).
- Often theoretically cleaner on **long horizons** (14–28 days), where recursive error compounding becomes significant.

**Disadvantages:**
- **More models to train**: 28× the computational cost (or more with hyperparameter tuning).
- **Less training data per model**: If you have 1000 training windows, each `f_k` still sees 1000 windows, but you're training 28 separate models, so total data is spread thin.
- **Ignores inter-day correlation**: Each horizon is predicted independently; the resulting forecasts may violate logical consistency (e.g., total sales on days 1+2 might exceed the sum of individual predictions).

#### C4. StatsForecast is neither recursive nor direct
- StatsForecast uses neither strategy. Instead, it fits **one model per series** (one ARIMA, one ETS, etc.) and applies that model's equations repeatedly to produce the full horizon.
- This is distinct from recursive (no predicted values feed back as features) and from direct (no separate models per horizon).
- In practice, StatsForecast forecasts show **growing uncertainty** (wider prediction intervals) but **not the same error-accumulation pattern** as recursive prediction-feeding.

---

### Section D: Hybrid approaches and alternatives

**Lecture**, ~2 min.

- **MIMO (Multiple-Input, Multiple-Output)**: Train a single neural network to output all `h` steps at once, but with a rich internal representation (e.g., encoder-decoder). Avoids both recursion error (no feedback) and the 28× cost of direct models. This is what Chronos and TimesFM do. They don't fit the "recursive" or "direct" categories in the traditional sense; instead, they're conditioned on the entire history and produce a distributional forecast in one pass.
- **DirRec (Direct-Recursive hybrid)**: Predict 1–7 days using one recursive model, then 8–28 using separate direct models. Balances both approaches: captures short-horizon patterns via recursion, avoids long-horizon error accumulation via direct models.
- **MLForecast's direct mode**: The underlying MLForecast library supports direct forecasting (via `max_horizon` parameter), but MMF's current configuration does not expose it. Direct LightGBM is a potential future feature.

**In MMF (current):** MIMO is implicit in foundation models (Chronos, TimesFM); DirRec and direct LightGBM are not offered. Recursive MLForecast is the only global ML approach.

---

### Section E: Empirical comparison on M5

**Lecture + widget**, ~5 min.

#### E1. Recursive (MLForecastLGBM) vs. iterative equations (StatsForecast ETS, ARIMA)
- **Typical result on M5**: Average sMAPE over all 28 days often favors LightGBM or StatsForecast depending on series characteristics and configuration.
- **Per-day breakdown (Lab 4.1 evaluation)**: MLForecastLGBM (recursive) typically shows degrading accuracy: day 1 is usually better than day 28, partly because prediction errors feed back as lag features (the size of the gap on M5 is to be measured, not assumed). StatsForecast models (iterative equations) also degrade with the horizon; flat or repeating forecasts (Seasonal Naive, Croston/TSB) degrade mainly because the future drifts away from the last observed level or pattern.
- **Why both are useful**: LightGBM's lag-learning ability often outweighs error accumulation; simple statistical models are robust baselines whose degradation is easy to anticipate.

#### E2. Foundation models (Chronos) vs. statistical and ML
- Chronos (MIMO) typically shows **nearly flat per-day accuracy** — minimal decay.
- On zero-heavy M5 series, foundation models can be competitive or outperform both statistical and traditional ML models.

#### E3. Widget: Show error decay curves
- Plot: average sMAPE by day (1, 2, …, 28) for 3–4 model classes (e.g., ETS, ARIMA, LightGBM, Chronos).
- Highlight the recursive (LightGBM) curve decaying; iterative (ETS, ARIMA) showing gentler degradation; MIMO-like (Chronos) nearly flat.
- **Interactive**: Let learners pick a series (Typical item, Spare part, Promotion) and see how the pattern shifts with series characteristics.

---

## 4. Interactive / visual component

**Widget: Error Accumulation Explorer**

A self-contained HTML/SVG/JavaScript widget, following the pattern of `_backtest_explorer.py` and `_metric_explorer.py`.

### Parameters (sliders)

1. **Series type** (dropdown): Steady seller, Intermittent, Promotions, Custom.
   - Pre-fills a synthetic series with realistic characteristics.

2. **Model strategy** (radio buttons): Recursive, Direct, Hybrid (DirRec, 7-day split), MIMO-like.
   - Determines how the forecast is computed in the widget.

3. **Forecast error magnitude** (slider): 0% to 20%, default 5%.
   - Injects a random error on each step (for recursive) or each horizon (for direct).
   - Controls the noise / model quality.

4. **Model persistence** (slider): -0.5 to 1.0, default 0.7.
   - Controls the lag coefficient: how much weight the lagged value gets.
   - At 0.5: forecasts revert to mean (damping), errors decay.
   - At 1.0: forecasts are a random walk (unit root), errors persist or grow.
   - At -0.5: forecasts oscillate, errors alternate.

5. **Horizon** (slider): 1 to 28 days, default 28.
   - How many days ahead to forecast.

### Panels

**Panel 1: The data and 28-day forecast**
- Time series plot, last 60 days of history + 28-day forecast horizon.
- Four forecast lines: Recursive, Direct, Hybrid, MIMO.
- Light shading shows ±1 std dev error bands (growing for recursive, constant for direct).

**Panel 2: Per-day accuracy (sMAPE)**
- Line plot: sMAPE by day (1–28) for each strategy.
- Recursive curve should show upward trend (degrading accuracy).
- Direct curve should be flat.
- Hybrid curve should be flat for days 1–7, then show a kink at day 8 (where it switches).

**Panel 3: Cumulative error**
- Area chart or line plot: cumulative absolute error across the 28-day horizon.
- Recursive curve rises more steeply than direct (error compounds).

**Panel 4: Distribution of errors (100 alternative histories)**
- Box plot or violin plot showing error distributions for each strategy.
- For recursive: wider boxes / higher max errors (due to compounding).
- For direct: narrower, consistent boxes.

### Presets (buttons)

- **"Steady seller with perfect model"** (type: Steady, error: 1%, persistence: 0.7).
  - All strategies perform similarly because the series is predictable and error is minimal.

- **"Intermittent with noisy model"** (type: Intermittent, error: 15%, persistence: 0.5).
  - Recursive degrades noticeably; direct is more stable.

- **"Random walk series"** (type: Custom, error: 5%, persistence: 1.0).
  - Errors don't decay; recursive and direct diverge sharply by day 28.

- **"Series with negative autocorrelation"** (type: Custom, error: 5%, persistence: -0.3).
  - Forecast oscillates; recursive errors alternate sign; direct errors accumulate (both bad).

- **"Change strategy"** (interactive): Let the user pick a series and then A/B test two strategies by clicking buttons.

### Maths verification

- **Recursive error**: On step *k*, error is `e_k = ε_k + α × e_{k-1}`, where `ε_k ~ N(0, σ²)` is the step *k* forecast error and `α` is the persistence coefficient. Solve recursively: `e_k = ε_k + α × ε_{k-1} + α² × ε_{k-2} + …`. The standard deviation grows: `std(e_k) = σ × sqrt((1 + α² + α⁴ + …))`.
- **Direct error**: On horizon *k*, error is `e_k = ε_k` (independent). No accumulation.
- **Widget simulation**: At each step, draw `ε_k ~ N(0, σ²)` (where `σ = error_magnitude`), apply recursion, and plot.

**Verification method:** A Node.js prototype will:
1. Generate 100 synthetic series of each type (steady, intermittent, etc.).
2. For each series and each strategy, run the widget's forecast logic.
3. Compare per-day sMAPE to theoretical expectations:
   - Recursive: sMAPE should increase by ~`sqrt(1 + α²)` per step (if `α` is constant).
   - Direct: sMAPE should remain flat.
4. Report max deviation; target < 1%.

Results stored in `SPECS/THEORY_MULTISTEP_VERIFY.txt`.

---

## 5. Data, setup and runtime

**No MMF data required.** The widget runs entirely in the browser with synthetic series.

### Optional: Real Lab 3.3 / Lab 4.1 results breakdown

If learners run Lab 3.3 (Provision and Execute) with MLForecastLGBM (recursive) and StatsForecast (iterative equations), Lab 4.1 (Best Model per Series) shows per-day evaluation results. A follow-up section visualizes:

1. **Extract evaluation results** per day (join `evaluation_output` on `day_of_forecast`).
2. **Plot sMAPE by day** for a few representative series (one typical, one intermittent, one with promotions).
3. **Compare recursive vs. iterative curves**: How fast do LightGBM and the statistical models degrade with the horizon on the reference results, and does LightGBM degrade faster, as recursion suggests?

This section is optional and runs as a static example (no execution required; uses reference results from Lab 4.1).

---

## 6. Files to create / change

### New files

- `labs/Source/en_us/notebooks/M03/3.5 Appendix - Multi-Step Forecasting and Error Growth.py`
  - Landing notebook, references the widget, theory explanation, and optional real-world breakdown.
  - Includes `Includes/Classroom-Setup-3.5.py` (nothing to set up; uses synthetic data).

- `labs/Source/en_us/notebooks/Includes/_multistep_explorer.py`
  - Contains `MULTISTEP_EXPLORER_HTML` string (self-contained widget).
  - Companion file (not run as notebook): `SPECS/THEORY_MULTISTEP_VERIFY.txt` (verification report).

### Existing files to update

- `SPECS/TODO.md`: Mark item as `[x]` once approved.
- `labs/Source/en_us/notebooks/M03/3.3 Lab - Provision and Execute with Genie Code.py` and `3.2 Demo - MMF with mmf_sa.py`: Add a brief note (e.g., "💡 Advanced: Multi-step forecasting strategies differ between model classes; see 3.5 Appendix for details").

---

## 7. Test plan

1. **Widget renders** in the Databricks output iframe (Chrome, Firefox, Safari, dark mode).
2. **Sliders and presets update controls** without errors.
3. **Per-day accuracy curves** match theoretical expectations:
   - Recursive (LightGBM): sMAPE increases with day, following error-growth model `std(e_k) = σ × sqrt(1 + α² + α⁴ + …)` (verify on 3 preset combinations).
   - Iterative (ETS, ARIMA): error also grows with the horizon, through the model's own state equations (verify on 3 preset combinations).
4. **100-draw robustness** (Panel 4) — error distributions match the plotted curves to within ±5%.
5. **Optional section** runs without error on a workspace with Lab 4.1 results (skips if results unavailable).
6. **Hyperlinks** to 3.2 and 3.3 work (if all lessons are present).

---

## 8. Decisions for the reviewer

1. **Status: Appendix (M03 · 3.5), not core.**
   - *Confirmed per SPEC_INDEX.md.* Optional for learners interested in multi-step trade-offs. The 2-hour core does not include it.

2. **Multi-step terminology corrected.**
   - *Fixed:* StatsForecast is neither "recursive" (doesn't feed predictions back) nor "direct" (doesn't train separate models per horizon). It uses iterative equations. MLForecast is recursive with lag-feeding. Direct mode exists in mlforecast but is not exposed by MMF.

3. **Should hybrid/DirRec be in the widget, or just theory?**
   - *Recommended: Include in the widget* (radio button). It's a bridge between the two extremes and shows trade-offs graphically. But don't require learners to understand it deeply; keep the theory section brief (Section D, ~2 min).

4. **Which series types should the synthetic data use?**
   - *Recommended: Steady seller, Intermittent, Promotions* (same as in `_backtest_explorer.py`). These are realistic M5 profiles and learners recognize them.

5. **Should we add a per-day breakdown to Lab 4.1?**
   - *Recommended: YES, as an optional cell ("For the curious").* Helps learners verify theory against real Lab 4.1 results.

---

## 9. Risks and out of scope

### Risks

- **Simulation accuracy**: The widget assumes a simple AR(1) lag model; real models (LightGBM) have nonlinear lags. *Mitigation:* Use the optional real breakdown (3.2 Demo / 3.3 Lab results) to show the theory is directionally correct, not exact.
- **Learner confusion with terminology**: "Recursive", "direct", "iterated" are used interchangeably in the literature. *Mitigation:* Define each upfront and link to FPP3 / Taieb et al. references.
- **Overconfidence in one strategy**: Learners may think "direct is always better because it avoids error accumulation." *Mitigation:* Emphasize that short-horizon recursive often wins, and that Chronos (MIMO) avoids both problems.

### Out of scope

- **Multi-step boosting** (gradient-boosted decision trees trained on multi-output loss). Complex; out of scope for this appendix.
- **Reconciliation of multi-step forecasts across a hierarchy.** See SPEC_HIERARCHICAL_RECONCILIATION (4.5 Appendix).
- **Training LightGBM in direct mode.** That's a feature request for MMF, not a lecture.
- **Probabilistic multi-step forecasting** (e.g., recursive with quantiles). See Spec 1 (prediction intervals) instead.

---

## 10. References

### Academic

- **Hyndman & Athanasopoulos (2021)**, *Forecasting: Principles and Practice*, 3rd ed.
  - Ch. 9: [Multiple regression models](https://otexts.com/fpp3/regression.html) (discusses AR lags and multi-step).
  - Note: The online version doesn't have a dedicated "Multi-Step Strategies" chapter; the content is scattered. Complemented by Taieb et al. below.

- **Taieb et al. (2012)**, ["Machine Learning for Time Series Forecasting with Application to Electricity Load Forecasting," *Neurocomputing*, 135, pp. 89–109.](https://doi.org/10.1016/j.neucom.2013.06.040)
  - Foundational paper comparing recursive, direct, and MIMO strategies. Defines error accumulation formally.

- **Makridakis & Hibon (2000)**, ["The M3-Competition: Results, Conclusions and Implications," *International Journal of Forecasting*, 16(4), pp. 451–476.](https://doi.org/10.1016/S0169-2070(00)00057-1)
  - M3 competition findings: statistical (direct-like) models often beat more complex methods on short horizons.

- **Cerqueira et al. (2020)**, ["Machine Learning for Time Series Forecasting: A Survey," *ACM Computing Surveys*, 54(4), pp. 1–35.](https://doi.org/10.1145/3236911)
  - Comprehensive review with a section on multi-step strategies and neural approaches (MIMO).

### Software & tools

- **StatsForecast** (Nixtla): Direct forecasting by default. [Docs](https://github.com/Nixtla/statsforecast)
- **MLForecast** (Nixtla): Recursive by default; can be switched to direct (requires custom wrapper). [Docs](https://github.com/Nixtla/mlforecast)
- **LightGBM**: Regression module, applied recursively in MLForecast. [Docs](https://lightgbm.readthedocs.io/)
- **Chronos** (Anthropic): MIMO-style transformer. [Docs](https://github.com/amazon-science/chronos-forecasting)
- **TimesFM** (Google): MIMO-style model. [Docs](https://github.com/google-research/time-series-foundation-models)

### MMF upstream

- `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/mlforecast/MLForecastPipeline.py` (lines 286–312): Implementation of recursive multi-step prediction.
- `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/models_conf.yaml` (lines 315–340): MLForecastLGBM and MLForecastAutoLGBM configuration (lags, target transforms, recursive by default).
- `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/statsforecast/StatsFcForecastingPipeline.py`: Direct multi-step via StatsForecast's native `forecast()`.

### Datasets

- **M5 Forecasting - Accuracy** (Kaggle): <https://www.kaggle.com/competitions/m5-forecasting-accuracy>
  - 28-day horizon; per-day results available in detailed submissions.
