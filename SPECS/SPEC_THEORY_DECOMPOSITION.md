# SPEC — Theory: Decomposition and Stationarity

| | |
|---|---|
| **TODO item** | [ ] Theory: decomposition and stationarity — trend / seasonality / remainder, why ETS, ARIMA and Theta behave as they do, why MMF's LightGBM uses `differences_1` (lecture, e.g. 2.1) |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson / artefact** | **2.1 Lecture — Structure and Quality of Time Series** (merged with data-quality lecture; optional, outside 2-hour core) |
| **Type / time** | Lecture (20–30 min) + interactive widget (STL-like decomposition explorer) |
| **Compute** | Serverless (no Spark job; runs in the browser) |

## 1. Goal and outcomes

Teach participants why time series models work — understanding that forecasting is not magic but rests on recognizing structure (trend, seasonality, noise) and removing it (stationarity) before fitting. By the end of this lesson:

1. **Explain** a decomposition (trend, seasonality, remainder) and why it matters: models learn patterns better when the data is stationary.
2. **Recognize** when a series is non-stationary (mean/variance change over time) and how differencing removes trend.
3. **Predict** why ETS, ARIMA and Theta models work on retail data: they decompose or difference automatically, so they handle trend and seasonality.
4. **Link** MMF's LightGBM choice of `differences_1` to the decomposition strategy: differencing the target makes the global model's features (lags, rolling means, date features) more predictive.
5. **Choose** when to apply decomposition vs differencing: local univariate models (ETS, ARIMA) do it internally; global ML models (LightGBM) need the engineer to prepare the target.

## 2. Background — what MMF supports (verified with source refs) / technical background

### 2.1 MMF model classes and decomposition

From `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/models_conf.yaml`:

**Local statistical models** (StatsForecast):
- `StatsForecastAutoETS`: Exponential Smoothing. ETS decomposes into **Error**, **Trend** (additive or multiplicative none/linear/damped) and **Seasonal** (none/additive/multiplicative). It learns the decomposition automatically.
- `StatsForecastAutoArima`: AutoRegressive Integrated Moving Average. **Integrated (I)** means differencing to achieve stationarity (the `differences_1` concept applied per-series).
- `StatsForecastAutoTheta`: Classical Theta method. Decomposes using a trend line and mean-centred seasonality. Uses `decomposition_type: "multiplicative"` in the config.

All three are *univariate* — they work per-series, so they can adapt the decomposition to each series' behaviour.

**Global ML model** (MLForecast):
- `MLForecastLGBM`: LightGBM trained once across all series. Features include `lags: [1, 7, 14, 28]`, `date_features: ["dayofweek", "month", "quarter"]`, and **`target_transforms: ["differences_1"]`** (from models_conf.yaml). The differencing is applied to the target *before* feature engineering, making the lagged features stationary.

### 2.2 Decomposition and stationarity: theory

**Decomposition** separates a time series into components:
- **Trend** (μ(t)): long-term direction (e.g. sales growing from 2020 to 2024).
- **Seasonality** (s(t)): repeating patterns within a year (e.g. Christmas spikes every December; Friday sales > Monday sales).
- **Remainder / noise** (ε(t)): what's left after removing trend and seasonality.

A series can be decomposed additively (y(t) = μ(t) + s(t) + ε(t)) or multiplicatively (y(t) = μ(t) × s(t) × ε(t)), depending on whether the seasonal swings grow as the level grows.

**Stationarity** means the series has constant mean, variance and autocorrelation over time (no trend, no seasonal jumps). Most classical forecasting models assume stationarity; they learn better on stationary data because the fitted coefficients remain valid. To achieve stationarity from a non-stationary series:
- **Differencing**: y'(t) = y(t) − y(t−1) removes trend. Seasonal differencing y''(t) = y(t) − y(t−7) removes weekly seasonality. (`differences_1` in MMF = lag-1 differencing.)
- **Transformation**: logarithms or Box-Cox stabilise variance.
- **Detrending**: subtract a fitted trend line.

### 2.3 Why ETS, ARIMA and Theta succeed on retail data

M5 is retail (Walmart daily sales) with strong weekly patterns and occasional promotions:
- **ETS** automatically selects the decomposition (additive or multiplicative, trend shape, seasonal pattern) and fits level / trend / seasonality on each series. Fast, robust to intermittent demand.
- **ARIMA** uses differencing (the *I* in ARIMA) to remove trend and any seasonality (if seasonal differencing is applied), then fits autoregressive and moving-average terms on the stationary residuals. Performs well when the order is right (often auto-detected).
- **Theta** uses a classical trend decomposition: fits a linear trend, decomposes the series into trend and seasonality via harmonic analysis, and forecasts each component independently. Interpretable and stable.

All three adapt per-series. For M5's intermittent and lumpy series (many zeros, occasional large spikes), the Croston family (TSB, ADIDA, IMAPA) is explicitly designed: they model the demand count and magnitude separately.

### 2.4 Why LightGBM uses `differences_1`

LightGBM is a global model: it trains once across all series, so it cannot adapt the decomposition per-series. Instead, the engineer prepares the target by differencing. This:

1. **Removes trend**, making the lagged features [1, 7, 14, 28] more predictive (lags capture the pattern, not the level).
2. **Stabilises the feature-target relationship** across series with different levels (a series at level 1,000 and one at level 100 both have the same difference structure).
3. **Avoids feature interaction problems**: without differencing, LightGBM must learn that high-lag values are informative only when the trend is known, a harder task.

After differencing, the global model predicts the difference ŷ'(t). To recover the original scale, the Skill accumulates: ŷ(t) = ŷ(t−1) + ŷ'(t).

### 2.5 References

- **Hyndman & Athanasopoulos, *Forecasting: Principles and Practice (3rd ed.)***, chapters:
  - 3 "Time series decomposition" (additive and multiplicative): https://otexts.com/fpp3/decomposition.html
  - 3.1 "Classical decomposition": https://otexts.com/fpp3/classical-decomposition.html
  - 8 "ARIMA models": https://otexts.com/fpp3/arima.html (differencing, unit roots, the ADF test)
  - 8.8 "Non-stationary models": https://otexts.com/fpp3/non-stationary.html
  - 7 "Exponential smoothing": https://otexts.com/fpp3/ets.html (ETS decomposition)

- **Montero-Manso & Hyndman (2021)**: "Principles and algorithms for forecasting groups of time series: locality and globality", *International Journal of Forecasting* 37:2, 686–701. [https://doi.org/10.1016/j.ijforecast.2020.11.002](https://doi.org/10.1016/j.ijforecast.2020.11.002) — directly addresses why global models differ from local: global models trade flexibility (can't adapt per-series) for stability (learn from all series).

- **StatsForecast Theta**: https://github.com/Nixtla/statsforecast#theta (decomposition_type parameter).

- **MLForecast and target transforms**: https://github.com/Nixtla/mlforecast (target_transforms in the pipeline; differences_1 is lag-1 differencing via NumPy).

## 3. Proposed content (outline; for slides: slide-by-slide outline)

### 3.1 Learning objectives (opening frame)

- Decompose a retail time series into trend, seasonality and remainder; identify when each dominates.
- Explain stationarity and why models need it.
- Connect differencing to removing trend: why `differences_1` is in MMF's LightGBM.
- Map ETS, ARIMA and Theta models to decomposition strategies.

### 3.2 Decomposition concept (lecture frames with visuals)

**Slide A:** A retail time series (M5, Walmart daily sales) overlaid with:
- **Trend line** (long-term growth or decline).
- **Seasonal pattern** (weekly spikes, promotions).
- **Remainder** (noise, unpredictable week-to-week variation).

Explain: trend and seasonality are predictable; remainder is noise. The "remainder" is where the model must learn from historical patterns (lags, other features).

**Slide B:** Decomposition formula:
- Additive: y(t) = μ(t) + s(t) + ε(t). Use when seasonality is constant (same magnitude each year).
- Multiplicative: y(t) = μ(t) × s(t) × ε(t). Use when seasonality grows with the level (e.g. more noise at high sales).

Show on the same M5 series which applies (check with the widget below).

### 3.3 Stationarity (lecture frames)

**Slide C:** Define stationarity: mean, variance and autocorrelation are constant over time. Show a non-stationary example (trend upward, variance increasing) and a stationary one (mean-centred noise).

**Slide D:** Why models need stationarity:
- A model trained on the first half of a non-stationary series may fail on the second half (the level has changed).
- ARIMA and ETS work by learning patterns in *differences*, not raw values, so differencing makes them more robust.

**Slide E:** Differencing as a tool:
- **Lag-1 differencing**: y'(t) = y(t) − y(t−1). Removes trend. Example: M5 sales go 100, 110, 105, 120 → differences 10, −5, 15. The differences are smaller in magnitude and have no trend.
- **Seasonal differencing**: y''(t) = y(t) − y(t−7). Removes weekly seasonality.
- **Order of differencing**: if one difference isn't enough (ADF test shows non-stationarity), apply a second: y''(t) = y'(t) − y'(t−1). Rare in retail data.

### 3.4 Why local models work

**Slide F:** ETS (Error-Trend-Seasonal) decomposition in action:
- Fits a trend (level, slope, damping) and seasonal factors for each series.
- Forecasts by extrapolating trend and repeating seasonality.
- Adapts: a series with strong trend gets a trend term; a flat series does not.

**Slide G:** ARIMA via differencing:
- Auto-detects the differencing order (usually 0 or 1 for retail; d=0 means stationary, d=1 means one difference needed).
- Fits AR (autoregressive) and MA (moving average) on the stationary residuals.
- Undoes the difference to get forecasts in the original scale.

**Slide H:** Theta — trend + seasonality:
- Fits a trend line (often linear).
- Extracts seasonality as the residual (actual − trend).
- Forecasts by extending trend and repeating/interpolating seasonality.

### 3.5 Why global (ML) models need preparation

**Slide I:** LightGBM trades adaptability for scale:
- Trains once across all series → must work for series at level 1 and level 1,000.
- Uses features (lags, date features, rolling means) to capture patterns.
- Problem: a raw lag-1 value (e.g., 95) can mean very different things for a series at level 100 vs level 10,000.

**Slide J:** Differencing solves this:
- Before differencing: series A (level ~50) and series B (level ~500) have different lag magnitudes.
- After differencing: both have differences in the range −20 to +20 (relative to their variance).
- Lag features become comparable across series; the model learns: *"high difference followed by another high difference → trend continues"* (one rule for all series).

**Slide K:** The transformation pipeline for LightGBM:
1. Difference the target: y'(t) = y(t) − y(t−1).
2. Compute features on the original series (or differenced, depending on the lag). Lags: [1, 7, 14, 28] on the differenced target.
3. Train the model to predict y'(t) from features.
4. Forecast by accumulating: ŷ(t) = ŷ(t−1) + ŷ'(t).

### 3.6 Interactive widget: Decompose and stationarity explorer

A self-contained HTML/SVG/JS widget (in the spirit of 3.1 Lecture and 4.2 Appendix) lets participants:

1. **Choose a synthetic or real M5 series** (Steady seller, Intermittent, Promotional).
2. **Decompose** it using a "classical STL-like" method (trend via local polynomial, seasonality via repeating pattern).
3. **Visualise** trend, seasonality and remainder as separate lines.
4. **Check stationarity**:
   - Show the original series and first differences side-by-side.
   - Estimate mean / variance of each; highlight if mean is changing.
   - Run a simplified ADF test indicator (not the real statsmodels ADF, but a heuristic: variance of rolling mean vs within-window variance).
5. **Presets** for common M5 patterns:
   - "Steady seller": low variance, clear seasonality.
   - "Intermittent": many zeros, occasional spikes.
   - "Promotional": regular promotion weeks with jumps.
6. **Toggle** between additive and multiplicative decomposition.
7. **Show answers** to questions like:
   - "Which component is largest?" (trend, seasonality, noise).
   - "Is the series stationary?" (Yes/No, with reason).
   - "How many differences are needed?" (0, 1, or 2).

**Widget design:**
- Left: Time series plot with the chosen decomposition (trend line, seasonal bands, remainder as scatter).
- Middle: Decomposition bars (% contribution of each component).
- Right: Original vs differenced (stationarity comparison); a simplified ADF indicator.
- Controls: slider for series length, dropdown for decomposition method (classical additive, multiplicative, or STL), toggle for differencing order.

**Preset scenarios** (copy-paste from NOTES.md 2026-10-18 for accuracy):
- Steady seller (low intermittency): Stable decomposition, additive works well, differencing is stable.
- Intermittent (many zeros): Decomposition is harder; remainder is large; differencing still helps.
- Promotional (regular spikes): Trend is masked by promotions; multiplicative decomposition reveals it.

## 4. Interactive / visual component (if any)

**Yes:** STL-like decomposition explorer widget (self-contained HTML/SVG/JS, 1,000–2,000 lines, following the pattern of 3.1 and 4.2). Presets, toggles, and re-renders on the client.

Alternative: A Databricks visualization (SQL query on M5 reference data with a decomposition table) if the browser widget is out of scope.

## 5. Data, setup and runtime / build

- **Data:** Synthetic M5-like series (Steady seller, Intermittent, Promotional) embedded in the widget, seeded RNG. Alternatively, load a few real M5 series from `mmf.m5` and display them.
- **Setup:** None beyond the widget definition. The lesson has no prerequisites; it runs on Serverless.
- **Runtime:** < 5 min to read and interact.
- **Build:** Widget definition notebook (`Includes/_decomposition_explorer.py`) defines `DECOMPOSITION_EXPLORER_HTML`; lesson displays it with `displayHTML`. Optionally packaged as a Typst slide in the deck (§SPEC_PRESENTATION_TYPST).

## 6. Files to create / change

| File | Action | Notes |
|------|--------|-------|
| `labs/Source/en_us/notebooks/M02 - Preparing Many Series/2.1 Lecture - Structure and Quality of Time Series.py` | Create | Main lecture notebook; sections on data quality checks and decomposition/stationarity. |
| `labs/Source/en_us/notebooks/Includes/_decomposition_explorer.py` | Create | Self-contained widget defining `DECOMPOSITION_EXPLORER_HTML`. ~1,500 lines HTML/SVG/JS. |
| `labs/Source/en_us/notebooks/Includes/Classroom-Setup-2.1.py` | Create | Standard setup; no prerequisites. |
| `setup/VERSIONS.md` | No change | (Reference only; no new external dependencies.) |

## 7. Test plan

1. **Widget rendering:** Import the widget notebook and run `displayHTML(DECOMPOSITION_EXPLORER_HTML)` in a serverless job (environment `client: "4"`). Verify it renders in the Databricks output iframe (no console errors).
2. **Widget interaction:** Test all presets and toggles in a browser; confirm stationarity indicator and differencing logic.
3. **Lesson flow:** Open 2.1 cold (no prerequisites) on a Vocareum-provisioned workspace. Check that learning objectives are clear and the widget matches the lecture narrative.
4. **Integration:** Verify 2.1 complements 2.2 (Prep and Clean) and 2.3 (Profile and Classify, Skill 2) without redundancy.

## 8. Decisions for the reviewer (numbered, with a recommended option)

**Decision 1: Accept the 2.1 slot assignment?**

*Assigned:* **2.1 Lecture — Structure and Quality of Time Series** (per SPEC_INDEX.md). Scope: decomposition, stationarity, and data-quality checks (imputation, anomaly capping, series length). Optional, outside the 2-hour core; follows 2.2 Demo (Prep and Clean).

*Rationale:* Data quality and decomposition are **prerequisites** for understanding why certain model classes are chosen. A unified 2.1 lecture gives learners a coherent mental model: a series is forecastable if (1) it has enough non-missing data, (2) it has structure (trend/seasonality), and (3) that structure is captured by the chosen models.

**Accept this slot?** (Proceed with 2.1 as assigned, or reconsider.)

**Decision 2: Decomposition method in the widget**

*Options:*
- **Option A (recommended):** Classical additive decomposition (fit a trend via local polynomial or LOWESS, subtract to get seasonality, then remainder). Simple, interpretable, matches lecture narrative.
- **Option B:** STL (Seasonal and Trend decomposition using LOESS). More sophisticated, but harder to explain in a visual widget without a statsmodels call (which requires Spark/Python).
- **Option C:** FFT (Fourier) for trend and periodogram for seasonality. Very visual but less intuitive for retail audiences.

**Recommended:** **Option A**. It's teachable, reversible (add trend back to get seasonality), and aligns with the lecture's goal of intuition.

**Decision 3: Stationarity indicator in the widget**

*Options:*
- **Option A (recommended):** Simple heuristic (rolling mean ± 2σ; if it drifts, non-stationary).
- **Option B:** Real ADF test (run in Python, passed to the widget as a pre-computed result; slower but rigorous).
- **Option C:** Visual only: overlay fitted trend; if trend is flat, stationary.

**Recommended:** **Option A**. Fast, visual, and good enough for learners to recognise the concept. Include a note that "a real ADF test is more rigorous" if they want to check a real series.

**Decision 4: Real M5 series or synthetic?**

*Options:*
- **Option A (recommended):** Synthetic M5-like series (seeded RNG, same patterns as in the backtest widget) embedded in the notebook. Ensures reproducibility and fast rendering.
- **Option B:** Real M5 series (loaded from `mmf.m5` at lesson load time). Adds realism but slower; requires data fetch.

**Recommended:** **Option A**. Consistency with 3.1 and 4.2 appendices. If learners want real examples, they can use the lesson's follow-up labs.

## 9. Risks and out of scope

| Risk / Constraint | Mitigation |
|---|---|
| **Scope creep:** Merging with 2.1 Data Quality makes it a long lecture. | Cap at 40 min total. Data quality (imputation, outliers) is facts; decomposition is concepts. Split if needed. |
| **Mathematical depth:** STL, ADF tests, ARIMA theory are academic. | Keep it intuitive. Formulas are optional; charts and examples are required. Reference FPP3 for rigor. |
| **Browser rendering:** Widget on very slow connections or old browsers may not render smoothly. | Test on Databricks' sandboxed output iframe (no external libraries; no network calls). Fallback: text explanation with static images. |
| **M5 specificity:** Decomposition behaviour is different for other industries (e.g. energy demand, financial data). | Acknowledge in the lesson. Frame as "retail case study"; note that concepts transfer. |

Out of scope:
- Hierarchical decomposition (e.g. X-11, X-13 by the US Census Bureau).
- Model-based decomposition (e.g. unobserved components models).
- Seasonal adjustment for publication (e.g. official retail indices).

## 10. References

1. **Hyndman, R. J., & Athanasopoulos, G. (2021).** *Forecasting: Principles and Practice (3rd ed.).* https://otexts.com/fpp3/
   - Sections on decomposition (§3), ARIMA (§8), exponential smoothing (§7).

2. **Montero-Manso, P., & Hyndman, R. J. (2021).** "Principles and algorithms for forecasting groups of time series: locality and globality." *International Journal of Forecasting*, 37(2), 686–701. https://doi.org/10.1016/j.ijforecast.2020.11.002

3. **StatsForecast Documentation.** https://github.com/Nixtla/statsforecast
   - Models: AutoETS, AutoARIMA, AutoTheta, Croston variants.

4. **MLForecast Documentation.** https://github.com/Nixtla/mlforecast
   - Target transforms (differences_1), feature engineering.

5. **MMF Source Code:** `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/models_conf.yaml` (model configs with target_transforms and decomposition options).

6. **FPP3 Chapter 3: Time Series Decomposition.** https://otexts.com/fpp3/decomposition.html

7. **FPP3 Chapter 8: ARIMA Models.** https://otexts.com/fpp3/arima.html
