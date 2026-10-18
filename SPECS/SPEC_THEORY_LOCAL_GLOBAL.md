# SPEC — Theory: Local vs Global Models

| | |
|---|---|
| **TODO item** | [ ] Theory: local vs global models — cross-learning across series, what global and foundation (zero-shot) models gain and lose; the theory behind 4.1's model-class comparison (lecture, e.g. 1.1) |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson / artefact** | **1.1 Lecture — Why Many-Model Forecasting: Local, Global and Foundation Models** (per SPEC_INDEX.md; optional, outside 2-hour core) |
| **Type / time** | Lecture (25–35 min) with optional interactive explorer |
| **Compute** | Serverless (no Spark job; runs in the browser) |

## 1. Goal and outcomes

Teach the trade-offs and complementary strengths of **local models** (per-series), **global models** (cross-series learning), and **foundation models** (zero-shot from diverse time series). This is the foundational "why" of MMF. By the end:

1. **Explain** why MMF uses three model classes, not one: each has different strengths.
2. **Describe** what local models gain (adapt per-series, handle intermittency, fast) and lose (no cross-learning, weak on new series).
3. **Describe** what global models gain (learn from all series, strong on high-volume series, stable) and lose (slow at irregular patterns, need many series, require careful feature engineering).
4. **Describe** what foundation models gain (zero-shot, trained on millions of time series, often beat statistical models) and lose (expensive inference, need GPUs, less interpretable).
5. **Use** the per-series best-model results in Lab 4.1 to show where each class wins: "Why did LightGBM win for series A but Theta for series B?"

## 2. Background — what MMF supports (verified with source refs) / technical background

### 2.1 Local models in MMF

**Definition:** A model trained independently on each series' history, with no information from other series.

**MMF's local models** (from `models_conf.yaml`): StatsForecast models:
- `StatsForecastAutoETS`: Error-Trend-Seasonal. Decomposes and fits per-series; adapts the decomposition type (additive vs multiplicative, trend presence, seasonality shape). **Flexible, interpretable, handles intermittency via innovations.**
- `StatsForecastAutoArima`: AutoRegressive Integrated Moving Average. Auto-detects the order (p, d, q) per-series. **Good at capturing temporal dependencies; slow on many series.**
- `StatsForecastAutoTheta`: Theta method. Fits trend + seasonality per-series. **Stable, simple, good at seasonal data.**
- `StatsForecastCrostonOptimized` (and variants ADIDA, IMAPA, TSB): **Explicitly designed for intermittent demand** (retail, spare parts). Models demand frequency and magnitude separately.

**How they work:** Each model is refitted on each backtest window (rolling-origin evaluation). At forecast time (after the full history), the model is refit once.

**Strengths:**
- Adapt to series-specific patterns: a series with trend gets a trend component; a flat intermittent series does not.
- Handle extreme values and irregular patterns naturally (ETS via innovations, ARIMA via differencing).
- No feature engineering required; the model learns from raw data.

**Weaknesses:**
- Cannot learn from other series: a new series is a blank slate.
- Slow on large volumes (100k series × 5 models = 500k refits per backtest).
- Perform poorly on very short histories (too few data points to fit parameters).

**References:**
- StatsForecast: https://github.com/Nixtla/statsforecast (models, auto-detection, parallelization).
- Hyndman & Athanasopoulos, *FPP3*, chapters 7–8 (ETS, ARIMA) and 5 (ARIMA for retail / Croston).

### 2.2 Global models in MMF

**Definition:** A single model trained on the combined history of all (or most) series, learning features and relationships that transfer across series.

**MMF's global model:** `MLForecastLGBM` (LightGBM via MLForecast).

**How it works:**
- Construct features from the history: lags [1, 7, 14, 28] on the differenced target, date features (dayofweek, month, quarter), rolling means.
- Train a single LightGBM regressor on all series concatenated.
- At inference, compute the same features from each series' history and predict.

**Why differencing?** Differencing (y'(t) = y(t) − y(t−1)) removes the level and trend from each series, making the target stationary. This helps LightGBM learn patterns in the differenced space (changes) rather than raw levels. Series at different scales still have different-magnitude differences, but the *pattern* is more comparable: both "jump up then stabilize" looks similar after differencing, even if one series has differences in the range [−100, +100] and another in [−10, +10]. MMF does not apply additional per-series scaling; LightGBM handles the magnitude variation through its learned feature coefficients.

**Strengths:**
- Learns from all series at once: patterns common to many series (day-of-week effect, promotion impact) are learned once and applied to all.
- **Strong on high-volume series:** If a series appears many times in the training data (or is similar to many others), the model has many examples to learn from.
- Stable: the single trained model reduces variance compared to per-series models.
- Scalable: one model, many series (no per-series refitting).

**Weaknesses:**
- Cannot adapt per-series: a series with multiplicative seasonality is treated the same as one with additive.
- Requires careful feature engineering: the `target_transforms: ["differences_1"]` choice is critical; wrong engineering breaks the model.
- Performs poorly on irregular series (high seasonality variation, many anomalies): the single model must average behaviour across diverse series, losing details.
- Needs enough series to learn from: on 10 series, LightGBM has little to learn; on 1,000, it shines.

**References:**
- MLForecast: https://github.com/Nixtla/mlforecast (feature engineering, scikit-learn pipeline).
- LightGBM documentation: https://lightgbm.readthedocs.io/ (boosting, feature importance, handling multiple series).
- Montero-Manso & Hyndman (2021): *"Principles and algorithms for forecasting groups of time series"* — directly addresses when local and global models excel.

### 2.3 Foundation models (zero-shot) in MMF

**Definition:** Models trained on millions of time series from diverse domains, then applied to new series *without any retraining*. They learn general patterns that transfer across domains.

**MMF's foundation models:** Chronos-2 and TimesFM 2.5 (via Nixtla / HuggingFace).

**How they work:**
- Pre-trained on large corpora (financial, energy, retail, weather, etc.). The model learns what a time series "looks like" and how to forecast given only recent history (zero-shot).
- At inference, encode the time series (recent values, possibly scaled/normalised) and decode predictions.
- No retraining, no feature engineering. Works on any new series.

**Why zero-shot?** Because the pre-training sees such diverse patterns that the model generalises. It doesn't need examples of the *specific* series you're forecasting; it learned the *grammar* of time series across domains.

**Strengths:**
- Work on new series with no historical retraining: "cold start" forecasting.
- Often outperform statistical and ML models on short histories (where local models lack data, and global models haven't seen similar patterns).
- General: same model across domains (retail, energy, finance).
- Interpretable latent space (the encoder represents the series in a learnable space).

**Weaknesses:**
- Require GPU for fast inference (modern foundation models are large transformers). CPU inference is slow.
- Expensive training and inference (pre-training on millions of series costs resources).
- Less transparent: harder to debug why the model failed than ETS (which has explicit components).
- May generalise *away* from domain-specific patterns: a model trained on energy demand might miss the detailed retail week-of-month effect.

**References:**
- Chronos (Nixtla): https://github.com/Nixtla/chronos (models, inference, evaluation).
- TimesFM (Google): https://arxiv.org/abs/2310.10688 (pre-training, zero-shot evaluation).

### 2.4 The M5 competition context

The M5 Forecasting competition (Kaggle, 2020) drove MMF's multi-model design:
- **Top solutions** used **LightGBM** (global) and ensemble techniques, because M5 is high-volume retail (30k series) with similar patterns across stores.
- **However**, LightGBM's dominance doesn't generalise: it thrives on volumes; on 100 series, statistical models often match or beat it.
- **Foundation models** were not available then (Chronos and TimesFM emerged 2023+), but retrospective studies show they would have been top-5 contenders.

**Lesson:** No single model wins everywhere. MMF runs all three (local, global, foundation), and **per-series best-model selection** (Skill 5 / Lab 4.1) picks the winner for each.

### 2.5 When does MMF use each?

| Model class | Dataset | Series characteristics | Why |
|---|---|---|---|
| **Local (ETS, ARIMA)** | Any size | Intermittent, irregular, seasonal, <100 data points | Adapt per-series; no cross-series info needed |
| **Global (LightGBM)** | 1,000+ series | Regular, similar patterns, high-volume, >365 data points | Learn from all; stable; fast inference |
| **Foundation (Chronos, TimesFM)** | Any size, especially small | Short history, new series (cold start), cross-domain patterns | Zero-shot; no retraining; strong on anomalies |

**Best practice:** Run all three on the same series; pick the best per-series. On M5 (100 series):
- LightGBM: best for high-volume stores with stable patterns.
- ETS / Theta: best for low-volume, seasonal-heavy series.
- Chronos: sometimes ties or beats LightGBM on irregular series.

## 3. Proposed content (outline; for slides: slide-by-slide outline)

### 3.1 Learning objectives (opening frame)

By the end of this lesson:
- Explain why MMF does not pick a single model; instead, it runs many and lets the data decide.
- Describe what local models do: adapt per-series, learn from the series' own history.
- Describe what global models do: learn from all series together, transfer knowledge.
- Describe what foundation models do: use pre-trained patterns, forecast without retraining.
- Predict which model class will win for a given series based on its characteristics (intermittency, volume, seasonality).

### 3.2 The multi-model motivation (opening frames)

**Slide A — The Problem:**
- You have 100–1,000 retail time series (item-store combinations). No single model is best for all.
- Series A: high-volume, stable, repeating day-of-week and promotion patterns → **global models learn well**.
- Series B: intermittent (many zeros, occasional spikes), small volume → **local models adapt; foundation models generalise**.
- Series C: new to the system (cold start), no history → **only foundation models work**.
- **Solution:** Run all three; pick the best for each series (per-series best-model selection).

**Slide B — Three model classes:**
A 3×3 matrix:
- **Axis 1 (Left):** Local (per-series) → Global (all-series) → Foundation (pre-trained).
- **Axis 2 (Top):** Interpretation (white-box) → Adaptability (per-series) → Scalability (inference speed).
- **Fill each cell with a model:**
  - Local: ETS, ARIMA, Theta (white-box, adapt per-series, slow on 30k series).
  - Global: LightGBM (grey-box, stable, fast on new series).
  - Foundation: Chronos, TimesFM (black-box, zero-shot, GPU needed).

### 3.3 Local models: adapt per-series (lecture frames with examples)

**Slide C — How local models work:**
- Train independently on each series' history (no info from other series).
- Refit at each backtest window; refit once at the end for production.
- Examples: ETS decomposes into trend + seasonality + error; ARIMA uses differencing to stationarise; Theta fits a trend line + seasonality.

**Slide D — ETS example on M5:**
- A series with clear weekly seasonality and slight uptrend: ETS fits Trend=Linear, Seasonal=Additive, Error=Additive.
- Same series next year with a promotion spike: ETS refits, adjusting for the new level.
- A flat intermittent series (many zeros): ETS fits Trend=None, Seasonal=None, error only (innovations-based).
- **Strength:** Each series gets the right decomposition.
- **Weakness:** No information sharing; a new series is a blank slate.

**Slide E — Croston for intermittent demand:**
- Standard models (ETS, ARIMA) assume continuous demand; they forecast the average, not the pattern.
- Croston, TSB, ADIDA: separate demand frequency (how often do we sell?) from magnitude (how much when we do?).
- Example: spare parts sell 2 days per month on average; Croston forecasts "no sale" most days, then spikes.
- **Unique strength:** Only local models handle intermittent demand well (global models treat zeros as noise).

**Slide F — Speed and scalability:**
- Local models must refit per-series: 100 series × 5 models × 9 backtest windows = 4,500 fits.
- With MLflow parallelisation (`applyInPandas` on Spark), this runs in minutes on serverless.
- **Strength:** Parallelisable; no single training step is expensive.
- **Weakness:** Total time scales linearly with series count (can be hours for 30k series).

### 3.4 Global models: learn across series (lecture frames with examples)

**Slide G — How LightGBM works:**
1. Construct features: lags [1, 7, 14, 28] from each series' history, date features (dayofweek, month, quarter), rolling means, etc.
2. Stack all series side-by-side (same features, different series).
3. Train one LightGBM to predict the target (differenced, so it learns stationary patterns).
4. At forecast time, use the trained model on each series' new features (no retraining).

**Slide H — The global learning advantage:**
- Series A (Walmart Electronics, store 1): sees promotions on Tuesday.
- Series B (Walmart Grocery, store 5): sees promotions on Wednesday.
- Series C (Walmart Home, store 12): sees promotions on Monday.
- LightGBM trains on all three and learns: *"Promotions happen; they boost sales; which day depends on the store and category."*
- **New series D:** LightGBM immediately captures the promotion effect, even if series D itself has few examples.
- **Local model:** Series D must learn from scratch; if it's only 2 months old, it may miss the promotion pattern.

**Slide I — Feature engineering is critical:**
- **Without differencing:** Raw target values and lags reflect the level of each series (high-volume series has large values; low-volume has small values). A single global model struggles to learn rules that work across both.
- **With differencing:** The target becomes differences (changes), which removes the level. Differences in pattern are more comparable across series: "sell more this week than last" looks structurally similar whether it's +100 units or +10 units. The model learns from the structure of changes, not the absolute level.
- This is why MMF uses `target_transforms: ["differences_1"]` in `models_conf.yaml`. Note: MMF does not apply per-series scaling; different-sized series still have different-magnitude differences, but the learned patterns generalize.

**Slide J — Strengths and weaknesses:**
- **Strengths:** Learn from all series; stable; fast at inference (no per-series retraining); strong on high-volume series.
- **Weaknesses:** One model for all → loses per-series nuance; requires careful feature engineering; performs poorly on irregular/rare series; needs many series to learn from (100 is minimum; 1,000+ is ideal).

### 3.5 Foundation models: zero-shot (lecture frames with examples)

**Slide K — What are foundation models?**
- Pre-trained on millions of time series from diverse domains (retail, energy, finance, weather, etc.).
- Encoder: reads a time series (e.g., last 512 days of sales) and compresses it into a learned representation.
- Decoder: given the representation, generates forecasts for the next 28 days (or any horizon).
- **Zero-shot:** no retraining or feature engineering; apply the pre-trained model directly to any new series.

**Slide L — Example: Chronos on M5.**
- Chronos was trained on 200M+ time series (mixing retail, energy, finance, etc.).
- It learned: *"Weekly patterns (Fourier basis), seasonal cycles (learnable), trend (exponential or linear), noise."*
- On M5 (never seen by Chronos during training), it forecasts well because the patterns are common (day-of-week, seasonal promotions, noise).
- **Compare:** ETS on a new M5 series must learn its trend + seasonality from scratch. Chronos already knows what "retail weekly seasonality" looks like.

**Slide M — Cold start and transfer:**
- **Cold start:** Series with 14 days of history (e.g. new SKU launched). Local models have too little data. Global models need many similar series in training. Foundation models work: they've seen millions of short-history series.
- **Transfer:** Energy-demand forecasting (sine waves, autocorrelation) transfers to retail (week-to-week repeats). One pre-training captures both.

**Slide N — GPU and interpretability trade-offs:**
- **GPU:** Foundation models are large (100M+ parameters); inference on CPU is slow (seconds per series × 1,000 series = hours). GPU inference: 10x faster.
- **Interpretability:** Why did Chronos forecast 100 units for series A but 50 for series B? The learned representation is a black box. No trend/seasonality decomposition to inspect.
- On M5 (retail, interpretability needed for planners), this is a trade-off. On pure volume forecasting, speed may win.

### 3.6 Comparison table: when does each win?

**Slide O — Decision tree:**

| Scenario | Local | Global | Foundation |
|---|---|---|---|
| **1,000+ series, similar patterns (M5 retail)** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **100 series, diverse patterns** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **Intermittent demand (spare parts)** | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| **New series (cold start, 14 days)** | ⭐ | ⭐ | ⭐⭐⭐ |
| **Interpretability / explainability** | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Speed (CPU, no GPU)** | ⭐⭐ | ⭐⭐⭐ | ⭐ |

### 3.7 Best-model selection in practice (Lab 4.1 context)

**Slide P — Per-series wins from the M5 workshop:**
- Show the output of Lesson 4.1 (from reference results): a table of best models per series.
- Rows: series (item-store combinations, grouped by category and store).
- Columns: best model, WAPE, model class (local / global / foundation).
- Patterns: *"LightGBM wins for electronics (high-volume); ETS wins for grocery (seasonal, intermittent); Chronos ties with ETS on irregular series."*

**Slide Q — Why the patterns emerge:**
- **LightGBM leaders:** High-volume, stable stores. LightGBM learned cross-series promotion and day-of-week effects; it applies them well here.
- **ETS leaders:** Low-volume, intermittent (many zero days). ETS adapted per-series; it doesn't assume "zero is noise."
- **Chronos ties:** Series with complex patterns that neither local nor global captures perfectly. Foundation model generalises from its training corpus.

### 3.8 Optional: interactive explorer

A lightweight widget (inspired by 3.1 backtest explorer and 4.2 metric explorer) that lets participants:
1. **Choose a synthetic M5-like series** (High-volume+stable, Intermittent, Promotional, Cold-start).
2. **See forecasts from local (ETS), global (LightGBM mock), and foundation (Chronos mock)** as lines on a chart.
3. **Observe errors** (MAE, RMSE) in a table, highlighting the winner.
4. **Change the series' characteristics** (volume, seasonality strength, history length) and watch the winner change.
5. **Explain the winner:** *"Chronos wins because …"* (pops up as text).

This widget is optional; the lecture works without it. If included, ~500–1,000 lines HTML/SVG/JS.

## 4. Interactive / visual component (if any)

**Optional:** Interactive explorer (HTML/SVG/JS) allowing participants to toggle through M5-like series and see which model class wins and why. Similar structure to the backtest and metric explorers (3.1 and 4.2).

**If omitted:** Slides with charts and the 4.1 Lab results (reference table of best models per series).

## 5. Data, setup and runtime / build

- **Data:** Synthetic or real M5 series (from `mmf.m5_reference` or embedded in widget). No Spark job needed; lecture runs on Serverless.
- **Setup:** None; lesson has no prerequisites. If including the widget, define it in `Includes/_local_global_explorer.py`.
- **Runtime:** 30–40 min (lecture) + 10 min (optional widget interaction).
- **Build:** Lecture notebook (`1.1 Lecture - Why Many-Model Forecasting.py`) + optional widget (`Includes/_local_global_explorer.py`).

## 6. Files to create / change

| File | Action | Notes |
|------|--------|-------|
| `labs/Source/en_us/notebooks/M01 - Many-Model Forecasting Foundations/1.1 Lecture - Why Many-Model Forecasting: Local, Global and Foundation Models.py` | Create | Main lecture notebook; sections on local, global, and foundation model trade-offs. |
| `labs/Source/en_us/notebooks/Includes/_local_global_explorer.py` (optional) | Create | Interactive widget (self-contained HTML/SVG/JS). Defines `LOCAL_GLOBAL_EXPLORER_HTML`. |
| `labs/Source/en_us/notebooks/Includes/Classroom-Setup-1.1.py` | Create | Standard setup; no prerequisites. |
| Lesson 1.2 Demo | No change | (Already exists; follows 1.1 naturally.) |

## 7. Test plan

1. **Lecture flow:** Open as a cold lesson (no prerequisites). Verify learning objectives are clear, slides are readable, and the narrative builds (local → global → foundation).
2. **Widget (if included):** Run on serverless in a Databricks job (environment `client: "4"`). Render in the output iframe; test all presets and toggles.
3. **Lab 4.1 integration:** After running lesson 4.1, check that reference results (best models per series) match the lecture's predictions (e.g., "LightGBM wins for high-volume series").
4. **Audience feedback:** Dry-run with a test participant. Check that they understand *why* MMF uses three model classes (not just *that* it does).

## 8. Decisions for the reviewer (numbered, with a recommended option)

**Decision 1: Accept the 1.1 slot assignment?**

*Assigned:* **1.1 Lecture — Why Many-Model Forecasting: Local, Global and Foundation Models** (per SPEC_INDEX.md). Scope: foundational theory on local vs global vs foundation model trade-offs. Optional, outside the 2-hour core; positioned before 1.2 Demo (Genie Code).

*Rationale:* Local vs global theory is foundational; placing it early (1.1) establishes the "why" for everything that follows (data prep, execution, evaluation).

**Accept this slot?** (Proceed with 1.1 as assigned, or reconsider.)

**Decision 2: Interactive explorer (include or omit)**

*Options:*
- **Option A (recommended):** Omit from 1.1 lecture; refer to Lab 4.1 results instead (reference table of best models per series). Simpler, avoids widget development time. The comparison table and Lab 4.1 results suffice.
- **Option B:** Include a lightweight explorer (series chooser + forecast comparison). Adds interactivity but ~500 lines of code to maintain.

**Recommended:** **Option A**. The lecture is already substantial; reference results from Lab 4.1 (post-execution) provide concrete examples. If time permits post-workshop, add the explorer as an enhancement.

**Decision 3: Foundation model depth**

*Options:*
- **Option A (recommended):** Conceptual level (Chronos is pre-trained on millions of series, applies to any new series, trades interpretability for zero-shot capability). Do not dive into transformer architecture or pre-training specifics.
- **Option B:** Include technical detail (encoder-decoder, attention, pre-training corpus composition, fine-tuning options). Risks overloading learners.

**Recommended:** **Option A**. Learners need intuition ("it's like a forecast model trained on everything") not deep learning theory. Defer technical depth to an optional Appendix or Blog Post.

**Decision 4: MMF-specific vs generalizable theory**

*Options:*
- **Option A (recommended):** Frame for MMF (3 classes, why each, per-series selection). But note that the theory generalises (any forecasting system faces this trade-off).
- **Option B:** Emphasize generalizable theory (local vs global is a fundamental ML trade-off), with MMF as one example.

**Recommended:** **Option A**. This is an MMF workshop; keep the focus on MMF's specific choices. Generalisations can be footnotes.

## 9. Risks and out of scope

| Risk / Constraint | Mitigation |
|---|---|
| **Complexity:** Local, global, and foundation models are deep topics. Covering all three in 30 min requires ruthless prioritization. | Focus on intuition (why) not math. Use analogies. Example: *"Local: expert on one patient; global: doctor sees 1,000 patients; foundation: doctor trained on 1M patients."* |
| **GPU dependency:** Foundation models need GPU for speed. If learners can't run them, this feels abstract. | Pre-computed reference results in `mmf.m5_reference` make foundation models concrete. Lab 5 shows them working. |
| **Generalization:** Is the multi-model strategy specific to retail (M5) or universal? | Acknowledge: *"Works on any domain with many similar series. Adapt model set for your domain."* |
| **Montero-Manso & Hyndman (2021):** Excellent reference but academic (2021 paper, assumes research audience). | Cite it, but translate key insights to plain language for practitioners. Footnote for depth-seekers. |

Out of scope:
- Ensemble methods and forecast combination (if local + global + foundation should be averaged or if best-model selection is better). See SPEC_THEORY_COMBINATION (4.4 Appendix).
- Hierarchical forecasting (forecast at item level, then reconcile to category level; MMF Skill 6 covers this).
- Online / streaming forecasting (model updates as new data arrives). Beyond workshop scope.
- Custom local models (e.g., user-defined SARIMA orders). Workshop uses auto-detection.

## 10. References

1. **Montero-Manso, P., & Hyndman, R. J. (2021).** "Principles and algorithms for forecasting groups of time series: locality and globality." *International Journal of Forecasting*, 37(2), 686–701. https://doi.org/10.1016/j.ijforecast.2020.11.002

2. **Hyndman, R. J., & Athanasopoulos, G. (2021).** *Forecasting: Principles and Practice (3rd ed.).* https://otexts.com/fpp3/
   - Chapters 7 (ETS), 8 (ARIMA), 5 (intermittent demand / Croston).

3. **StatsForecast Documentation.** https://github.com/Nixtla/statsforecast
   - Models: AutoETS, AutoARIMA, AutoTheta, Croston variants; parallelization via applyInPandas.

4. **MLForecast Documentation.** https://github.com/Nixtla/mlforecast
   - LightGBM integration, feature engineering (lags, date features, target transforms).

5. **Chronos (Nixtla).** https://github.com/Nixtla/chronos
   - Foundation model for time series; pre-training, zero-shot evaluation, HuggingFace release.

6. **TimesFM (Google).** https://arxiv.org/abs/2310.10688
   - Transformer-based foundation model; pre-training, zero-shot capability, comparison with Chronos and statistical models.

7. **M5 Forecasting Competition — Kaggle.** https://www.kaggle.com/c/m5-forecasting-accuracy/discussion
   - Top solutions using LightGBM and ensembles; discussions on local vs global strategies.

8. **MMF Source Code:** `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/models_conf.yaml` (model configs, framework choices).
