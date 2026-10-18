# SPEC — Foundation Models in Depth

| | |
|---|---|
| **TODO item** | Foundation models in depth: zero-shot Chronos / TimesFM / Moirai vs statistical and ML models — where they win (short or noisy series); needs GPU, so instructor-led, with the precomputed Chronos-Bolt results as the CPU fallback |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | 6.1 Lecture + Demo — Foundation Models in Depth (elective, M06 module) |
| **Type / time** | Lecture + Demo; elective; ~25 min lecture + optional ~15 min live demo |
| **Compute** | Lecture: none (slides/visuals). Demo: GPU (instructor-led G1 only) for live runs; CPU pre-computed reference results as fallback |

## 1. Goal and learner outcomes

By the end of this lesson you can:

- Explain the strengths and limitations of foundation models (Chronos-2, TimesFM 2.5) vs statistical (ARIMA, ETS, Seasonal Naive) and global ML (LightGBM) models.
- Describe zero-shot transfer: why a model trained on millions of series generalizes to your data without fine-tuning.
- Identify scenarios where foundation models **win:** short histories, very noisy data, new domains. And where they **don't:** abundant clean history, well-engineered features for a known domain, extreme intermittency.
- Read the MMF evaluation table and compare model classes by speed and accuracy.
- Understand the compute and cost trade-offs: GPU requirements, inference time, suitability for different scale deployments.

## 2. Background — what MMF supports

**Foundation models in MMF:**

- **Supported models:** Chronos-Bolt (Tiny, Mini, Small, Base), Chronos-2, Chronos-2-Small, Chronos-2-Synth, TimesFM-2.5-200m, all zero-shot. (Moirai is currently disabled since February 2026, per the upstream README.)
- **How they work:** MMF registers them as pre-trained models in Unity Catalog. During the backtest, `run_forecast()` calls the model's `predict()` method — **no retraining, no fine-tuning**.
- **Point forecasts only:** Foundation models generate sampled forecasts (multiple quantiles). MMF evaluates the **median** of these samples, storing only the point forecast in evaluation tables.
- **GPU requirement:** All foundation models require GPU (A10G, T4, or serverless GPU) for practical inference speed. On CPU they work but are 10–50× slower, which is why Vocareum uses pre-computed reference results.

**Where foundation models come from:**

- **Chronos-2** (Amazon Science): Trained on a large proprietary corpus; specialized for time series; available in multiple sizes (Small, Large); supports exogenous variables.
- **TimesFM-2.5** (Google Research): Trained on a diverse set of foundation model tasks; multi-horizon capability; supports LoRA fine-tuning (see Lesson 6.2).
- **Moirai** (Salesforce / uni2ts): Currently disabled in MMF since February 2026, per the upstream README; was known for handling intermittent demand. Not featured in this lesson.
- **Pretraining details:** all are trained on thousands to millions of time series; trained on multiple forecasting horizons and frequencies. None requires domain data at inference time.

## 3. Proposed content

### Section A. The zoo: model classes and what they trade (10 min, slides + live table)

**Model classes in MMF:**

| Class | Example | Training | Inference | Speed | Strength | Weakness |
|-------|---------|----------|-----------|-------|----------|----------|
| **Local (statistical)** | Seasonal Naive, AutoETS, AutoARIMA | Per-series; quick | Per-series | Fast (CPU, seconds) | Interpretable; cheap to train | Limited to simple patterns; requires sufficient history |
| **Local (intermittent)** | Croston, ADIDA, IMAPA, TSB | Per-series; quick | Per-series | Fast (CPU, seconds) | Handles zero-heavy and sporadic demand | Assumes demand structure; not for trending data |
| **Global ML** | LightGBM | All series together; medium | Per-series batch | Fast to medium (CPU, minutes) | Learns cross-series patterns; uses features | Needs good features and clean data; tends to underfit on short histories |
| **Deep learning** | NeuralForecast (LSTM, NBEATSx, etc.) | All series; slow | Per-series batch | Medium (GPU, ~minutes) | Learns temporal patterns end-to-end | Requires lots of data; prone to overfitting; complex to tune |
| **Foundation (zero-shot)** | Chronos-2, TimesFM | Billions of series (external); done | No retraining needed | Medium to slow (GPU, ~seconds–minutes) | Generalizes without fine-tuning; handles short histories and noise | Large VRAM; slower at inference; may not know your domain |

**Cost and scalability:**

- **Cost per series:** local models ~$10⁻⁴ per month (serverless CPU); deep learning and foundation models ~$10⁻²–10⁻¹ per month (GPU).
- **Latency:** local/ML models 100 ms–1 s; foundation models 500 ms–10 s per forecast (depending on history length and model size).

### Section B. When each wins (10 min, lecture + visuals)

Use **real M5 examples** (shown in 4.1 evaluation table or live in the instructor demo):

#### Statistical models win:
- Clean, long histories (> 100 observations), strong seasonality (e.g., seasonal Naive on weekly data). Example: regular fast-moving items in M5 (soft drinks, water).
- **Cost:** pennies per forecast.

#### LightGBM wins:
- Medium histories (~50 observations), cross-series signals (e.g., store-wide promotions, holidays affecting all items). Example: most items in M5.
- **Trade-off:** needs features; if poorly tuned, loses to Seasonal Naive.

#### Intermittent-specific models (Croston, ADIDA, IMAPA, TSB) win:
- Sparse, zero-heavy series (e.g., slow-moving retail SKUs, spare parts). Example: niche items in M5 (toys, seasonal goods).
- **Cost:** negligible on CPU.

#### Deep learning (NeuralForecast) wins:
- Very long histories + large datasets (1000s of series), when you have GPU capacity. Example: real weather or electricity grids (not M5, which is too small).
- **Risk:** overfitting, need for tuning.

#### Foundation models (zero-shot) win:
- **Short histories** (< 50 observations): the model learned general patterns from pretraining. Example: new M5 stores or new item launches.
- **Noisy or unusual data:** foundation models are robust. Example: M5 series with one-off promotions or data quality issues.
- **New domains:** a domain you haven't forecasted before, e.g., you're a retailer trying to forecast manufacturing demand. No retraining needed.
- **First baseline:** you have no labeled data yet. Just point the model at the series and get a forecast.

#### Foundation models do NOT win:
- **Very clean, abundant historical data:** if you have 5 years of clean, daily sales with strong seasonality (like most M5 series), Seasonal Naive and LightGBM often beat Chronos-2. They already know the exact pattern.
- **Extreme intermittency:** zero-heavy series (>80% zeros). Foundation models expect some signal; Croston and TSB are better tuned for this.
- **Domain-specific features:** if you engineer custom features (e.g., marketing spend, competitor pricing) for LightGBM, an uninformed foundation model can't use them.

### Section C. Zero-shot transfer: how it works (5 min, conceptual)

**The core idea:**

Foundation models are trained as sequence-to-sequence or autoregressive models on many diverse series:
- Input: a historical window (e.g., 512 time steps).
- Output: a forecast (next 28 steps, or context-dependent).

During this training, the model learns:
- Seasonal patterns (weekly, yearly, etc.) across industries.
- Trend detection and change-point behavior.
- How to handle noise and outliers.
- Transfer: when you give it a new series with similar statistical properties (seasonal, trending, noisy), it already knows how to forecast.

**Why pretraining works:**

- Most time series share common patterns (daily/weekly seasonality, trends, mean reversion).
- A model trained on 1M series has seen many instances of each pattern, even if your specific series is new.
- No fine-tuning needed because the learned representations are general.

### Section D. The proof: live comparison (15 min, optional demo, runs during the lecture or pre-recorded)

**Instructor runs in real-time or shows video:**

Use the MMF evaluation output from lesson 4.1 (or pre-run for consistency):

1. **Filter the evaluation table:**
   - By series characteristics (short histories, intermittent, trending).
   - By model class (statistical vs ML vs foundation).

2. **Show the scatter plot or box plots:**
   - X-axis: model class.
   - Y-axis: SMAPE or MAPE across the selected series.
   - Overlay: individual series as points.

3. **Narrate the patterns:**
   - "For the 10 newest items (shortest history), Chronos-2 averages 1.2 sMAPE while Seasonal Naive averages 1.8."
   - "For the 50 most regular items, Seasonal Naive and LightGBM are within 0.01 sMAPE; Chronos is 0.05 higher."
   - "For intermittent items, TSB is best; Chronos and LightGBM overestimate."

4. **Show the run times:**
   - `SELECT model, COUNT(*), AVG(runtime_seconds) FROM m5_evaluation_output GROUP BY model ORDER BY runtime_seconds DESC;`
   - Emphasize the speed vs accuracy trade-off.

### Section E. Decision tree: which model to try first? (5 min, decision guidance)

Provide a simple flowchart (visual or text):

```
Do you have a labeled history of 100+ days per series?
  YES → Are the series seasonal or trending?
         YES → Try Seasonal Naive or AutoETS first (fast, cheap).
         NO → Try LightGBM (learns from all series at once).
  NO → Is your domain mature (e.g., established retail) or new to you?
         MATURE → Try LightGBM or Seasonal Naive if very regular.
         NEW → Try Chronos-2 zero-shot first; no fine-tuning needed.

Is your series zero-heavy or very sparse?
  YES → Try Croston, ADIDA, IMAPA, or TSB (specialized for intermittent demand).
  NO → Continue above.

Do you have GPU available and time to experiment?
  YES → Try a foundation model (Chronos-2 or TimesFM) and compare.
  NO → Stick to CPU models (statistical, LightGBM).
```

## 4. Interactive / visual component

**Optional: interactive widget** (similar to 4.2, but comparing model classes):

- **X-axis:** model class (Statistical, ML, Foundation, Intermittent).
- **Y-axis:** sMAPE (or user-selectable metric).
- **Filter:** by series characteristics (length, sparsity, trend).
- **Hover:** shows series name, actual sMAPE, forecast sample.
- **Insight:** "which series are outliers?" — e.g., series where Chronos beats LightGBM by >30%.

**Fallback (if time is short):** static bar charts or a pre-computed comparison table in the notebook.

## 5. Data, setup and runtime

**Input:** 
- `mmf.m5_reference.evaluation_output` (from lesson 4.1 reference results) or participant-generated `{user_schema}.m5_evaluation_output`.

**Output:** 
- Comparison figures and decision guidance (no new tables created).

**Compute:**
- Lecture: no compute.
- Optional live demo: GPU if running a new forecast; otherwise read pre-computed results from `mmf.m5_reference` (CPU-friendly, ~seconds to load and filter).

## 6. Files to create / change

**New files:**

- `labs/Source/en_us/notebooks/M02 - Preparing Many Series/2.4 Lecture - Foundation Models and Model Selection.py` — the lecture notebook (Markdown, no data dependencies).
- `labs/Source/en_us/notebooks/Includes/_foundation_comparison_widget.py` (optional) — HTML/JS widget comparing model classes.

**Modified files:**

- `labs/Source/en_us/notebooks/M03 - Running Forecasts at Scale/3.2 Demo - MMF with mmf_sa.py` — add an optional "Foundation Models in Depth" section that highlights foundation model results (no change to the core forecast logic).
- `labs/Source/en_us/notebooks/M04 - Evaluating and Selecting Models/4.1 Lab - Best Model per Series.py` — update the narrative to reference this lecture; add a decision-tree summary cell.

**Setup:**

- No changes to `setup/workspace_setup.py` (uses existing reference results).

## 7. Test plan

**Smoke test (any environment):**

- Lecture notebook renders and imports complete.
- If optional widget included: no JavaScript errors in the browser console.
- Comparison tables/figures render correctly with pre-computed data.

**Instructor dry run (with GPU, before delivery):**

- If running live demo: verify the eval table query completes in < 10 s.
- Screenshots match expected output (e.g., Chronos-2 shows lift on short-history series).
- Timings: lecture (25 min) + optional demo (15 min) = 40 min total.

**Checkpoint cell (if included):**

- Comparison table has columns: `model_class`, `avg_smape`, `median_runtime_s`, `series_count`.
- No SQL errors or missing rows.

## 8. Decisions for the reviewer

1. **Placement: Lesson 6.1 in M06 (GPU, instructor-led)?**
   - **Confirmed:** 6.1 Lecture + Demo in new M06 module. Elective (not core 2-hour), GPU-focused. G2 (Vocareum) uses pre-computed CPU reference results; G1 instructor can run live demo if GPU available.
   - **Sequencing:** Follows the core (M01–M04) and MLOps (M05). Participants understand MMF fundamentals before comparing advanced models.

2. **Which foundation models to feature?**
   - **Confirmed:** Chronos-2 and TimesFM-2.5 (both active in MMF). Mention Moirai as "currently disabled, Salesforce's specialization for intermittent demand."
   - **Reasoning:** learners see state-of-the-art; different models exist; understand why one may be chosen.

3. **Live demo or pre-recorded?**
   - **Recommended:** pre-recorded or slide-based comparison tables (deterministic, time-controlled). Live demo is optional but risky if GPU isn't available or jobs are slow.
   - **Trade-off:** live demo shows interactive exploration; videos/slides are safer and time-bounded.

4. **How deep on pretraining theory?**
   - **Recommended:** light touch (5 min, Section C). Mention "trained on 1M+ series; learned general patterns." Skip transformer details.
   - **Audience:** learners are practitioners, not researchers.

5. **Link to fine-tuning (Lesson 6.2)?**
   - **Recommended:** End 6.1 with a preview: "if zero-shot doesn't suffice, Lesson 6.2 covers fine-tuning Chronos-2 on your domain data (requires GPU)."

## 9. Risks and out of scope

**Risks:**

- **Representation:** if M5 doesn't show clear wins for foundation models (e.g., because the series are well-behaved retail data), the lesson may feel theoretical. Mitigation: select the shortest-history or noisiest subset of M5, or use a synthetic dataset where foundation models excel.
- **Compute:** live demo GPU may not be available. Mitigation: pre-compute and show results; learners see the same insights without waiting.
- **Moirai availability:** currently disabled; if re-enabled upstream, the spec should be re-reviewed.

**Out of scope:**

- Pretraining details (transformer architectures, loss functions, training curves).
- Fine-tuning (covered in SPEC_TSFM_FINETUNING).
- Multilingual or cross-lingual transfer (not relevant to forecasting).
- Hierarchical forecasting with foundation models (optional topic, not in the core course).

## 10. References

- **Chronos-2:** Ansari et al., Amazon Science. https://github.com/amazon-science/chronos-forecasting
- **TimesFM:** Garza & Mergenthaler, Google Research. https://github.com/google-research/timesfm
- **Moirai (uni2ts):** Salesforce Research. https://github.com/salesforce/uni2ts
- **GIFT-Eval:** foundation model evaluation benchmark for forecasting.
- **Nixtla StatsForecast:** intermittent demand models (Croston, ADIDA, IMAPA, TSB). https://github.com/Nixtla/statsforecast
- **MMF models README:** /tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/models/README.md
- **Databricks blog on foundation models with MMF:** (search "Databricks foundation models forecasting")
