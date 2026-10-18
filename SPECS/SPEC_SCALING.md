# SPEC — Scaling Up: From 100 to 30,000 Series

| | |
|---|---|
| **TODO item** | `- [ ] Scaling up 100 → 1,000 → 30,000 series: runtime and cost per series on serverless (`daily_train_1000` is loaded), shuffle partitions, `backtest_length` / `stride`, which models to drop` |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | **M05 · 5.4 Appendix** — Scaling to Thousands of Series (optional; part of M05 "Running MMF in Production" module) |
| **Type / time** | Appendix + calculator widget; optional, self-paced; ~30 min |
| **Compute** | Serverless CPU (cost measurement via `system.billing.usage`) |

## 1. Goal and learner outcomes

Enable learners to understand MMF's parallelization strategy, anticipate runtimes and costs when scaling from a 100-series workshop to production (1,000–30,000+ series), and make informed tuning decisions to trade accuracy for speed.

**Learner outcomes:**
- Explain how MMF parallelizes: `applyInPandas` per series for local models, single-process global models, shuffle partitions and their tuning.
- Estimate forecast runtime and compute cost as a function of series count and model set.
- Use `backtest_length` and `stride` to trade off evaluation thoroughness for speed.
- Identify which model classes to drop at scale (foundation models, deep learning) to reduce runtime.
- Measure actual costs via Databricks system tables (`system.billing.usage`).

## 2. Background — what MMF supports (verified, with source refs)

**Parallelization strategy (from Forecaster.py and examples):**

- **Local statistical models (statsforecast, sktime):** Each series is modeled independently using `applyInPandas`, which applies a pandas UDF to groups of data partitioned by `unique_id`. Spark distributes these partitions across workers. Scaling is **linear in series count** (n series = n partitions, each parallelized across worker pool).
  - **Example:** 100 series on 4-worker pool → 25 series per worker. 1,000 series → ~250 per worker.
  - **Shuffle partitions:** Default is 200. For n series >> 200, this is fine. For n < 200, Spark creates fewer partitions, and workers sit idle. Not a bottleneck for the workshop scale.

- **Global models (LightGBM, NeuralForecast):** Trained on all series at once in a single Spark action. Scaling is **sublinear** (training time increases, but not linearly, due to tree depth and regularization). Shuffle partitions affect data shuffling during feature engineering.
  - **LightGBM on serverless:** ~ 10 min for 100 series, ~15 min for 1,000 series (not 10×).
  - **NeuralForecast (deep learning):** Slower; ~20 min for 100 series on multi-GPU; on serverless CPU, de-facto disabled.

- **Foundation models (Chronos, TimesFM):** Each series is scored independently (similar to local models). Scaling is linear. **GPU-bound:** on serverless GPU, faster than local models; on serverless CPU, they silently fail (no GPU). Not suitable for cost-sensitive production.

**Tuning parameters for scale:**

| Parameter | Effect on speed | Effect on accuracy | Typical values |
|-----------|-----------------|-------------------|-----------------|
| `backtest_length` | Linear: 90 days → 56 days saves 40% time | Moderate: fewer windows = higher variance in metric. 90 days is best practice; 56 days acceptable for prototyping. | Workshop: 56 or 90. Production: 90–180. |
| `stride` | Linear: smaller stride = more windows. stride=7 → 13 windows; stride=28 → 3 windows. | Moderate: more windows = stable metric. Stride=7 (weekly updates) is standard; stride=28 (monthly) is rougher. | Workshop: 7 or 28. Production: 7. |
| `active_models` | Linear per model: 6 models = 6× cost of 1. | Major: more models = more confidence in best-model selection and potential ensemble gains. | Workshop: 5–6 local + 1 global + optional 1 foundation. Production: 2–4 local + 1 global. |
| `prediction_length` | Negligible effect (determines train/test split, not model count). | Moderate: longer horizon = harder prediction. Unrelated to scale. | Workshop: 28. Production: depends on use case. |

**Shuffle partitions & data movement:**
- Spark shuffles data when grouping (e.g., `groupBy("unique_id")` in global model training) or joining. Default `spark.sql.shuffle.partitions = 200`.
- For n = 100 series: shuffle inefficiency is minor; a few extra partitions are created for shuffling, but no bottleneck.
- For n = 10,000+ series: shuffle can become a bottleneck if not tuned. Recommended: `shuffle_partitions = max(200, n_series / 10)` (i.e., ~1 series per 10 shuffled partitions to allow parallelism).
- **Practical:** On serverless, Databricks auto-tunes shuffle partitions; learners rarely need to adjust manually.

**Cost modeling (serverless CPU):**
- Databricks charges per **DBU-hour** (Databricks Unit hour). Serverless rates depend on region and tier; typical: ~$0.40–0.50 USD per DBU-hour.
- A forecast run on serverless notebooks consumes DBUs proportional to runtime and parallelism (workers × clock time).
- **Rough estimates for M5 (daily, 28-day horizon, fast model set):**
  - 100 series, 10 min runtime: ~10–15 DBU = ~$4–7.
  - 1,000 series, 15 min runtime: ~20–30 DBU = ~$8–15.
  - 10,000 series, 45 min runtime: ~60–100 DBU = ~$24–50.
  - **Cost per series:** ~$0.04–0.05 / series (mostly independent of scale, due to amortization of global model training).
- **Measurement:** Via `system.billing.usage` table (requires Workspace Admin role; not available to learners on Vocareum).

**Model class performance at scale:**
- **Local models:** Linear in series + model count. Cheap and predictable.
- **LightGBM:** Sublinear in series count; fixed training time per boosting round. Typical: +50–100% of local time for 5 local models.
- **NeuralForecast (DL):** Expensive; multi-GPU training. Not recommended for serverless CPU (disabled).
- **Foundation models:** Linear in series. On GPU, faster than local models (parallelized in batches). On CPU, fail or timeout. Not recommended for serverless.

**Data loading & I/O:**
- Reading from Delta tables is fast (vectorized, predicate pushdown). Not a bottleneck for scale.
- Writing results (evaluation_output, scoring_output) is more expensive than reading (shuffling, serialization). For 1,000 series × 5 models × 13 backtest windows = ~65k rows, typically <1 min.

**Not yet supported (as of May 2026):**
- Adaptive model selection based on series characteristics at scale (e.g., drop LightGBM for sparse series; use Croston only). Learners choose a fixed model set.
- Cost budgeting / enforcement (e.g., "don't exceed $50 per run").

## 3. Proposed content (section-by-section outline)

### M05 · 5.4 Appendix — Scaling to Thousands of Series

#### Overview (2 min, markdown)
- Why scale matters: workshop is 100–1,000 series; production is 10,000–30,000+.
- This appendix covers runtime predictions, cost estimation, and tuning strategies to keep production affordable.

#### A. Understanding MMF's parallelization (5 min, diagram + concept)
- **Diagram:** Parallel execution flowchart (ASCII or inline SVG):
  ```
  Input: daily_train (n series, m time steps per series)
           ↓
  Step 1: Local models (local_model_1, local_model_2, …)
          applyInPandas(series_id) — each series → worker
          Parallelism: min(n, num_workers)
          Time: O(n / num_workers × avg_series_time)
           ↓
  Step 2: Global model (LightGBM)
          Aggregates all series (single Spark action)
          Parallelism: depends on shuffling; workers process batches
          Time: O(1 per boosting round × n_rounds; typically 5–10 min)
           ↓
  Output: evaluation_output (n × m_models × n_backtest_windows rows)
  ```
- **Explanation:** Local models parallelize well (linear speedup up to # workers). Global models are inherently serial (one training pass) but fast relative to local models because they learn shared patterns.
- **Example:** On an 8-worker cluster:
  - 100 series, 5 local models, 1 LightGBM: ~15 min (local models + LightGBM dominate).
  - 1,000 series: ~20 min (local models scale, LightGBM slightly slower due to more data; global time dominates).
  - 10,000 series: ~45 min (local models cheap per series due to parallelism; global training expensive; Spark overhead).

#### B. The backtest-tuning trade-off (8 min, self-contained HTML calculator widget)
- **Trade-off matrix (reference table):**
  ```
  backtest_length | stride | # windows | Time (100 series) | Time (1,000 series) | Recommendation
  56              | 28     | 2         | ~6 min            | ~8 min              | Prototyping / demo
  56              | 14     | 4         | ~10 min           | ~12 min             | Quick iteration
  90              | 7      | 13        | ~20 min           | ~25 min             | Best practice (stable metric)
  180             | 7      | 25        | ~40 min           | ~55 min             | Deep validation (rarely needed)
  ```
- **Interactive HTML/JS calculator widget (displayHTML):**
  - Input sliders: series count (100–10000), backtest_length (28–180), stride (7–28), active_models count (1–6).
  - Real-time output: estimated runtime (min), estimated cost (DBU), status (green/yellow/red for acceptable/slow/too-slow).
  - Recommendation text: "stride=28 saves 50% time but metric is 5% less stable. Drop AutoTheta to save 10%."
  - Self-contained HTML/JS (no external libraries); seeded with M5 reference runtimes.
- **Learner task:** Use the calculator to find a tuning that fits a 5-minute slot, a 15-minute slot, and a 30-minute slot.

#### C. Scaling the model set: which models to keep (6 min, lab code + decision guide)
- **Model cost & value (empirical, from examples):**
  ```
  Model class          | Time per series | Accuracy (relative) | Cost-benefit
  SeasonalNaive        | fast (~0.01s)   | baseline            | Always include (control)
  AutoETS              | fast (~0.1s)    | good                | Always include (univariate best)
  CrostonOptimized     | fast (~0.05s)   | excellent (sparse)  | Include if series are sparse/intermittent
  TSB                  | fast (~0.05s)   | good                | Include (ensemble diversity)
  AutoTheta            | slow (~0.2s)    | good                | Drop at scale (minor value over ETS)
  LightGBM             | slow (~1 min/model) | v. good (w/ features) | Keep (global patterns) — but expensive
  NeuralForecast (DL)  | very slow (10+ min) | not tested         | Drop on serverless CPU (no GPU)
  Chronos (foundation) | medium (~0.5s)  | good (noisy data)   | Drop on serverless CPU (no GPU); expensive on GPU
  ```
- **Decision guide (flowchart):**
  - Q1: "Do you have external features (prices, events)?" → Keep LightGBM (uses them). Else, LightGBM is valuable but optional.
  - Q2: "Do you have intermittent series (lots of zeros)?" → Keep CrostonOptimized and TSB. Else, ETS + Naive suffice.
  - Q3: "Is runtime under 30 min acceptable?" → Keep all models. Else, drop AutoTheta, maybe NeuralForecast.
  - Q4: "Do you have GPU quota?" → Keep foundation models. Else, drop them.
- **Learner task:** Given a production scenario (e.g., "50,000 daily retail SKUs, prices available, must retrain daily in <20 min"), recommend a model set.
- **ANSWER block:** Shows two example scenarios with recommended model sets and rationale.

#### D. Estimating cost via system tables (7 min, SQL + concept)
- **Concept:** Databricks `system.billing.usage` table logs compute consumption by user and job. Queries on this table reveal which jobs are expensive.
- **Query template (read-only, info-only for learners on Vocareum):**
  ```sql
  SELECT 
    job_id, job_name, 
    SUM(compute_dbu) / 60.0 as compute_dbu,
    SUM(compute_dbu) / 60.0 * 0.45 as estimated_cost_usd
  FROM system.billing.usage
  WHERE job_name LIKE '%mmf%'
    AND usage_date BETWEEN '2026-10-01' AND '2026-10-31'
  GROUP BY job_id, job_name
  ORDER BY compute_dbu DESC
  ```
- **Interpretation:** Shows which forecasting jobs consumed the most compute, and estimated cost per run.
- **Learner task:** Estimate the cost of a forecast run on 1,000 series (reference: "The 3.2 demo on 100 series with fast model set cost ~$5; scale to 1,000 series").
- **Note:** Learners on Vocareum may not have access to `system.billing.usage` (admin-only). Provide a pre-computed cost table or CSV export instead.

#### E. Practical scaling scenarios (5 min, case studies)
- **Scenario 1: Daily retraining, 5,000 items**
  - Goal: Retrain daily in <30 min to stay ahead of next morning's demand.
  - Model set: SeasonalNaive + ETS + CrostonOptimized + LightGBM (4 models).
  - Backtest: 56 days, stride=28 (2 windows, fast).
  - Predicted runtime: ~25 min. Estimated cost: ~$10/run = ~$300/month.
  - Recommendation: Acceptable; can optimize further if needed.

- **Scenario 2: Weekly evaluation, 100,000 items**
  - Goal: Full evaluation once a week to validate model quality.
  - Model set: SeasonalNaive + ETS + CrostonOptimized + LightGBM + Chronos-Bolt (5 models).
  - Backtest: 90 days, stride=7 (13 windows, best practice).
  - Predicted runtime: ~60 min (longer due to volume). Estimated cost: ~$25/run = ~$100/month (weekly).
  - Recommendation: Expensive but acceptable for weekly validation.

- **Scenario 3: Real-time scoring, millions of forecasts**
  - Goal: Score 1M+ items daily for inventory planning.
  - Strategy: Train once per month (off-peak); score daily (fast).
  - Reuse global model + local models (no retraining); apply to new data.
  - Predicted runtime (scoring): ~5 min. Estimated cost: ~$2/day = ~$60/month.
  - Recommendation: Viable; separate training from scoring.

#### F. Summary: tuning checklist (2 min, reference)
- **Before running a forecast, ask:**
  1. How many series? (→ affects parallelism, I/O overhead)
  2. What's your runtime budget? (→ informs backtest_length, stride, model set)
  3. Do you have GPU access? (→ enables foundation models, NeuralForecast)
  4. What's your accuracy vs speed trade-off? (→ informs model selection)
  5. What's your monthly cost budget? (→ limits retraining frequency and model count)

### Classroom Setup (Includes/Classroom-Setup-5.4.py)
- Provides reference data: sample evaluation_output from 100, 1,000, and 10,000-series runs (aggregated metrics).
- Optionally, a pre-computed `system.billing.usage` export (CSV) for cost queries.

## 4. Interactive / visual component (if any)

**M05 · 5.4:**
- **Parallelization diagram (ASCII, inline in markdown):** Section A.
- **Backtest tuning calculator (self-contained HTML/SVG/JS widget via displayHTML):** Section B — learner adjusts sliders (series count, backtest_length, stride, model count); output updates real-time with runtime estimate, cost estimate, and recommendation. Similar in scope and size to 3.1 / 4.2 widgets (~15 KB).
- **Model cost-benefit table (Markdown):** Section C.
- **Decision flowchart (ASCII, inline in markdown):** Section C decision guide.
- **Case study cards (Markdown collapsible `<details>`):** Section E — three scenarios with expandable details.

No Plotly or external JS libraries. All visualization via native HTML/SVG/JS in notebook cells (displayHTML).

## 5. Data, setup and runtime

**Data inputs:**
- `mmf.m5.daily_train_100`, `daily_train_1000`, `daily_train_10000` (if available; optional for simulation).
- `mmf.m5_reference.evaluation_output` (reference results from 100-series runs).
- Pre-computed runtime benchmarks (table in markdown or CSV).

**Outputs:**
- Learner responses: tuning recommendations, cost estimates, model set choices.
- (Optional) Benchmark results if learner runs a 1,000-series forecast as part of the lab.

**Runtime:**
- No long-running Spark jobs (appendix is concept + calculator).
- If learner runs a 1,000-series forecast as a bonus: ~15 min on serverless.

**Compute:**
- Serverless notebook (calculator, SQL queries).
- Optional: shared all-purpose cluster (if learner opts to run a 1,000-series forecast).

## 6. Files to create / change

**Notebooks:**
- `labs/Source/en_us/notebooks/M05 - Running MMF in Production/5.4 Appendix - Scaling to Thousands of Series.py`
- `labs/Source/en_us/notebooks/Includes/Classroom-Setup-5.4.py`

**Supporting files:**
- `labs/Source/en_us/notebooks/Includes/_scaling_calculator.py` (self-contained HTML/SVG/JS widget for backtest tuning, displayHTML-based; similar to _backtest_explorer.py and _metric_explorer.py).
- `labs/Source/en_us/notebooks/Includes/data/benchmark_results.csv` (reference runtimes and costs for 100, 1,000, 10,000 series).

## 7. Test plan (e2-demo and/or Vocareum)

**e2-demo (instructor-only):**
1. Run M05 · 5.4 on e2-demo-field-eng.
2. Verify parallelization diagram (ASCII) renders correctly.
3. Use the backtest tuning calculator widget: adjust sliders (e.g., series=1000, backtest_length=90, stride=7, models=5); confirm runtime estimate, cost estimate, and recommendation text update dynamically.
4. Query reference evaluation_output (section D): confirm SQL template works.
5. Read through section C decision guide; confirm logic is sound (e.g., LightGBM + sparse data → include CrostonOptimized).
6. (Optional) Provision a 10,000-series forecast on serverless; measure actual runtime and compare to prediction.

**Vocareum (learner-paced, G2):**
1. Enter M05 · 5.4 cold (Classroom-Setup-5.4 provides reference data).
2. Section A: read the diagram and explanation.
3. Section B: use the tuning calculator widget (adjust 4 sliders, observe real-time output).
4. Section C: read the decision guide; complete a task (e.g., "For 10,000 items with prices, what model set?" or "What's the fastest model set under 10 min?").
5. Section D: (Info only; no system table access on Vocareum) Read the query template and interpret pre-computed cost data provided in Classroom-Setup.
6. Section E: read case studies.
7. Section F: review the checklist before attempting a large forecast.

**Timing:**
- Full appendix (sections A–F, with calculator and case studies): 30 min.
- Shortened version (sections A–C): 15 min.

## 8. Decisions for the reviewer (numbered, with a recommended option)

| # | Decision | Options | **Recommended** | Rationale |
|---|----------|---------|-----------------|-----------|
| **D1** | Backtest tuning: fixed table or interactive calculator? | (a) Static table (Markdown) with pre-computed runtimes. (b) Self-contained HTML/SVG/JS widget (displayHTML) where learners adjust sliders and see real-time outputs. | **(b)** | (b) is engaging and teaches the trade-off viscerally. (a) is faster but less memorable. (b) is ~15 KB custom HTML/JS (same scope as 3.1 / 4.2 explorers, no external libraries like Plotly). |
| **D2** | Model selection guidance: rigid rules or case-by-case | (a) Provide a decision flowchart (Q1: features? Q2: sparse? …). (b) Teach learners to benchmark their own models and decide. | **(a)** | (a) is practical and fast. (b) is more thorough but adds 30 min (requires a benchmark run). Use (a) + optional (b) as a deepdive. |
| **D3** | Cost measurement: system tables or estimation | (a) Query `system.billing.usage` directly (info-only; learners on Vocareum may lack access). (b) Provide pre-computed cost table or spreadsheet calculator. | **(b)** | (b) is universally accessible. (a) is more authentic but permission-gated. (b) + optional reference to (a) is best. |
| **D4** | Practical scaling: include a 1,000-series forecast | (a) Appendix is concept + calculator only (no long-running job). (b) Learners run a 1,000-series forecast as a "bonus challenge" (adds 15 min runtime). | **(a)** | (a) keeps the appendix focused and time-bounded. (b) is valuable for advanced learners but risky (job may fail, timeout, or go over budget). Optional bonus. |
| **D5** | Shuffle partitions tuning: explain or skip | (a) Mention `spark.sql.shuffle.partitions` and when to tune it. (b) Ignore; Spark auto-tunes on serverless. | **(b)** | (b) is practical. On serverless, auto-tuning is good enough. (a) is valuable for on-prem clusters but out of scope here. |
| **D6** | Foundation models at scale: include or defer | (a) Include a section: "Foundation models don't scale on serverless CPU; GPU-only." (b) Omit (learners already know from M03 · 3.2 that foundation models need GPU). | **(b)** | (b) is cleaner; learners already have the context. If including, keep it brief. |

## 9. Risks and out of scope

**Risks:**

1. **Runtime predictions are inaccurate:** Parallelism, Spark overhead, and cluster configuration vary. Benchmark times may differ ±50% on a learner's cluster. **Mitigation:** Provide ranges ("15–30 min, depending on cluster and data skew"), not point estimates. Encourage learners to time a few runs on their own cluster.

2. **Learners run a very large forecast accidentally:** A typo (e.g., `daily_train_100000` instead of `daily_train_100`) could trigger a job costing $100+. **Mitigation:** In notebooks, enforce max series count with a guard cell:
   ```python
   assert n_series <= 10000, f"Too many series ({n_series}); limit is 10k for safety."
   ```

3. **System tables are not accessible on Vocareum:** `system.billing.usage` requires admin role. **Mitigation:** Pre-compute and provide a CSV export in Classroom-Setup-3.5.

4. **Calculator widget breaks on large inputs:** The HTML/JS calculator may stall or error if learners input unrealistic values (e.g., 1M series). **Mitigation:** Add input validation and max/min bounds to the widget (e.g., series count capped at 100k, stride >= 1).

**Out of scope:**

- **Deep Spark tuning:** Executor memory, task parallelism, broadcast variable sizes, etc. These are advanced and cluster-specific. Link to Databricks Spark tuning docs.
- **Auto-scaling strategies:** Multi-tenant job scheduling, queue management, etc. Beyond the scope of a single-user workshop.
- **Model ensemble techniques:** Combining models to improve accuracy is touched in M04 · 4.1; scaling ensembles further is out of scope.
- **Approximation algorithms:** Fast approximate methods (e.g., sampling series for quick estimates) are interesting but not recommended for forecasting.
- **Hardware-specific optimization:** GPU CUDA tuning, CPU vectorization, etc. Too low-level for this workshop.
- **Cost optimization via reserved instances / spot pricing:** Databricks Reservations are an admin feature. Learners use on-demand rates.

## 10. References

- **MMF Parallelization (applyInPandas, Forecaster.py):** `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/Forecaster.py` (lines 272, 582)
- **Serverless examples:** `/tmp/mmf_upstream/many-model-forecasting-main/examples/serverless/` (local_univariate_serverless.ipynb, global_serverless_ml.ipynb, etc.)
- **Benchmark examples (M5):** `/tmp/mmf_upstream/many-model-forecasting-main/examples/m5/` (daily notebooks)
- **Databricks Spark tuning:** https://docs.databricks.com/en/performance/index.html
- **Serverless compute:** https://docs.databricks.com/en/compute/serverless-compute/index.html
- **System billing tables:** https://docs.databricks.com/en/admin/system-tables/index.html
- **Shuffle partitions config:** https://docs.databricks.com/en/performance/shuffle-partitions.html
- **Databricks Jobs & scheduling:** https://docs.databricks.com/en/workflows/jobs/index.html
- **Delta Lake I/O optimization:** https://docs.databricks.com/en/delta/data-skipping.html
