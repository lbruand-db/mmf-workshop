# SPEC — MLOps with MMF: Drift, Retraining, Promotion and Monitoring

| | |
|---|---|
| **TODO item** | `- [ ] Let's add a lesson on MLOps` |
| **Status** | Draft for review — 2026-10-18 (revised: built on [lbruand-db/mmf-mlops](https://github.com/lbruand-db/mmf-mlops)) |
| **Proposed lesson** | **M05 · 5.1 Lab** — The MLOps Loop: Drift, Retraining and Promotion; **M05 · 5.2 Appendix** — Monitoring Forecast Accuracy (both optional; M05 *Running MMF in Production*) |
| **Type / time** | Lab ~45 min + Appendix ~30 min (runtimes to be measured) |
| **Compute** | Serverless CPU (notebooks, jobs); a SQL warehouse for the alert (5.2) |
| **Source** | `mmf-mlops` @ `main` (pushed 2026-10-01; private): `SPEC/SPECS.md` (deck + caveats C1–C8), `SPEC/SPECS_HANDSON.md` (hands-on design), `SPEC/DEMO_SCENARIO.md`, `demo/` (Asset Bundle + notebooks), `deck/` (Typst, same `typst-dbrx-template`) |

## 1. Goal and learner outcomes

Show the loop that turns MMF forecasts into an operated system — and be honest about which part MMF provides and which part you build. By the end, learners can:
1. Say what MMF owns (training, backtesting, scoring, registering global/foundation models) and what it does not (scheduling, monitoring, drift detection, retraining triggers, promotion, CI/CD).
2. Watch a model **drift**: a frozen Champion trained before a demand shock degrades after it.
3. **Retrain** a Challenger, compare it with the Champion on the shocked segment (WAPE and bias), and **promote** it by moving the Unity Catalog `champion` alias.
4. Turn MMF's backtest output into an accuracy-over-time table, and write the alert query that would trigger retraining (5.2).

## 2. Background

### 2.1 What mmf-mlops contains

A talk ("MLOps with MMF and MLflow, and the caveats") plus a runnable demo built to back it, on M5:

| `demo/` file | Role (Phase) |
|--------------|--------------|
| `databricks.yml`, `resources/jobs.yml` | Asset Bundle, dev / prod targets; jobs `mmf_setup`, `mmf_tick` (weekly cron, paused), `mmf_fast_forward`, `mmf_retrain`; `Project` / `Environment` tags; follows `databricks-solutions/mlops-quickstart` |
| `src/data_prep.py` | M5 subsample (~200 series) → `sales_full` (0) |
| `src/sim_clock.py`, `run_mmf.py`, `fast_forward.py` | `AS_OF` cursor via a `revealed_sales` view; MMF run at `AS_OF` (1–2) |
| `src/maturation.py` | Explode MMF `evaluation_output` windows (`forecast`/`actual` arrays) into `forecast_vs_actual` (one row per series × model × target day, with `horizon_days`) (2) |
| `src/metrics.py` | Weekly WAPE, sMAPE, bias per model × department × horizon bucket → `metrics` (2) |
| `src/monitoring.py` | Lakehouse Monitoring inference-log monitor on `forecast_vs_actual` (regression; sliced by department and horizon) (2) |
| `src/drift.py` | Inject a demand collapse: one department (default `HOBBIES_2`, the "spare parts" stand-in) × 0.3 from a shock date; idempotent via `sales_full_base` (3) |
| `src/champion.py` | Frozen global Champion: `MLForecastLGBM` via `run_forecast`, trained up to a pre-shock cutoff, forecasting far enough to cross the shock; registered in UC by MMF (3) |
| `src/promotion.py` | Champion vs Challenger WAPE / bias on the overlap window for the shocked segment; move the UC `champion` alias if the Challenger wins (3) |
| `src/alert.sql`, `build_dashboard.py` | Breach query behind a SQL alert (latest week, 1-week horizon, n ≥ 20, WAPE > threshold); AI/BI dashboard (3) |

Status (its README): phases 0–3 built and validated on a workspace; CI/CD (GitHub Actions) and recording still open.

**The key design lesson** (`SPECS_HANDSON.md` §3, revised after building): re-running MMF at every simulated tick is far too slow, and it never shows drift anyway — MMF refits at every window and every run, so it always adapts. So: the accuracy timeline comes from **one** MMF backtest (`evaluation_output` already holds a forecast at every origin), and the drift arc needs a **global** model **held fixed** across an injected shock. Local models stay in the story for caveat C1.

### 2.2 The caveats (from `SPECS.md` §6, checked against MMF at the course pin)

| | Caveat | At the pin (`322ef91`) |
|-|--------|------------------------|
| C1 | Local models aren't registered; they're pickled into Delta | Local scoring writes a `model_pickle` column; global scoring writes `model_pickle = b""` and a `model_uri` (`Forecaster.score_local_model` / `score_global_model`) |
| C2 | Pickles are tied to library versions | Pin and record versions (course: `setup/VERSIONS.md`) |
| C3 | MLflow runs and metrics explode at scale | Use the Delta evaluation table for per-series analysis |
| C4 | Serving depends on the family | Global / foundation: UC model + `model_uri`; local: batch only |
| C5 | Retraining, drift detection and monitoring are not built in | This lesson |
| C6 | Compute gotchas (Arrow, adaptive execution, shuffle partitions; reconciliation needs classic compute) | The course runs MMF on serverless (3.2, 3.4 tested) |
| C7 | Strict data contract | See 3.4 (regressors), 2.4 (cold start) |
| C8 | Match the model family to the data | See 4.1, 6.1 |

The deck's field evidence names customers and is marked "anonymize"; **no customer names in the course**.

### 2.3 MMF facts the lab relies on (verified at the pin)

- Global models are registered as `{model_output}.{model}_{use_case_name}` (lower-cased by UC, e.g. `mlforecastlgbm_m5_exog` in the 3.4 test); each `run_forecast` with the same `use_case_name` adds a **version** (`Forecaster.evaluate_global_model`: the model fitted on the full history is registered; scoring loads it by `model_uri`). **MMF sets no alias.**
- Aliases: `MlflowClient().set_registered_model_alias(name, "champion", version)`; read with `get_model_version_by_alias`. Unity Catalog has no stages.
- Scoring output: `ds` and `y` arrays per series, plus `run_id`, `use_case`, `model`, `model_uri`.

## 3. Proposed content

### 5.1 Lab — The MLOps Loop (≈ 45 min)

**A. Who owns what (5 min).** MMF vs the loop around it; caveats C1, C4, C5 (one line each).

**B. A shock (5 min).** Copy `daily_train_100` (+ `dept_id` from `m5_static_features`) to `{out}.sales_full`; apply the demand collapse to one department present in the sample (mmf-mlops' `drift.py` logic: `sales_full_base` snapshot, factor 0.3 from a shock date about two thirds through the last year). Plot the department's sales.

**C. The Champion (10 min).** `run_forecast` with `MLForecastLGBM`, trained up to a pre-shock cutoff, `prediction_length` long enough to cross the shock, `model_output={out}`, `use_case_name="m5_mlops"` → version 1. Set alias `champion` → 1.

**D. Drift (5 min).** Compare the Champion's forecast with the actuals after the shock, on the shocked department vs the rest: WAPE and **bias** climb on that department only. Positive bias = over-forecasting = stock nobody buys.

**E. Challenger and promotion (10 min).** Retrain with a post-shock cutoff (same `use_case_name` → version 2), compare both on the overlap window for the shocked department (mmf-mlops' `promotion.py` query), and move the alias if the Challenger wins. Read it back with `get_model_version_by_alias`.

**F. Make it a job (10 min).** Create the retraining job — notebook task, serverless, paused schedule — with the Databricks SDK from the notebook (or ask Genie Code, as in 3.3). Run it once; check the run and the new model version.

### 5.2 Appendix — Monitoring Forecast Accuracy (≈ 30 min)

**A. Accuracy over time from one backtest.** Run (or reuse) an MMF backtest with `stride=7` over the period; explode `evaluation_output` into `{out}.forecast_vs_actual` (`maturation.py`), aggregate weekly WAPE / bias by department and horizon bucket (`metrics.py`). WAPE and bias, not MAPE (zero days — 4.2).

**B. The alert.** The breach query (`alert.sql`): latest week, 1-week horizon, enough rows, WAPE above a threshold. Show where a Databricks SQL alert would run it and what it would trigger (the job from 5.1 F).

**C. Lakehouse Monitoring (optional).** The inference-log monitor (`monitoring.py`) on `forecast_vs_actual`, if available in the workspace; otherwise a matplotlib chart of the `metrics` table.

**D. Beyond the course.** Asset Bundles with dev / prod targets and CI/CD (GitHub Actions) — shown from mmf-mlops, not hands-on (needs the CLI and a Git provider).

## 4. Interactive / visual component

None new: matplotlib charts (department sales with the shock; WAPE / bias before and after; Champion vs Challenger). The Typst MLOps deck in mmf-mlops can supply slides for the instructor.

## 5. Data, setup and runtime

- **Inputs:** `mmf.m5.daily_train_100`, `mmf.m5.m5_static_features`.
- **Outputs (learner schema):** `sales_full`, `sales_full_base`, MMF evaluation / scoring tables for the champion and challenger runs, registered model `{out}.mlforecastlgbm_m5_mlops` (versions 1, 2; alias `champion`), and in 5.2 `forecast_vs_actual`, `metrics`.
- **Setup:** none beyond the course's (`Classroom-Setup-5.1` → `ensure_schema()`).
- **Runtime:** to be measured. Reference point: one `MLForecastLGBM` run on 100 series took about 2 minutes in the 3.4 test.
- **Versions:** the course pin (`322ef91`, `requirements-cpu.txt`), not mmf-mlops' `mmf_sa @ main` / `databricks-sdk==0.40.0`.

## 6. Files to create / change

| File | Action |
|------|--------|
| `labs/Source/en_us/notebooks/M05 - Running MMF in Production/5.1 Lab - The MLOps Loop.py` | Create — adapted from `drift.py`, `champion.py`, `promotion.py` |
| `labs/Source/en_us/notebooks/M05 - Running MMF in Production/5.2 Appendix - Monitoring Forecast Accuracy.py` | Create — adapted from `maturation.py`, `metrics.py`, `alert.sql`, `monitoring.py` |
| `labs/Source/en_us/notebooks/Includes/Classroom-Setup-5.1.py`, `-5.2.py` | Create |
| `AGENDA.py`, learner README, `SPECS/RESTRUCTURE.md` | Change — add M05 |

## 7. Test plan

1. On e2-demo: 5.1 end to end on 100 series — shock applied; Champion v1 and Challenger v2 registered; WAPE / bias climb on the shocked department only; alias moves; the job runs once. Record runtimes.
2. Pick the shocked department from those present in `daily_train_100` and enough series (the sample has 26 HOBBIES, 20 HOUSEHOLD, 54 FOODS series across departments — check counts per `dept_id`).
3. 5.2: `forecast_vs_actual` row count = series × windows × 28; the alert query returns rows after the shock and none before.
4. Vocareum: model registration and alias in the learner schema; job creation as a learner; SQL warehouse for the alert; whether Lakehouse Monitoring is available.

## 8. Decisions for the reviewer

1. **Reuse mmf-mlops code in the course:** (a) **port the needed notebooks into the course** (recommended — same author, so no licence issue; the repo is private, so learners couldn't follow a link); (b) make mmf-mlops public and link to it.
2. **Simulated time:** the Champion/Challenger arc on one shock (recommended — what mmf-mlops settled on) vs the `AS_OF` tick loop (too slow; mmf-mlops dropped it).
3. **Job creation:** SDK from the notebook (recommended — reproducible, works on Vocareum if learners may create jobs) vs Genie Code (fits the course theme; less predictable) vs the Jobs UI (screenshots).
4. **Monitoring in 5.2:** SQL `metrics` table + chart (recommended baseline) with Lakehouse Monitoring as an optional step, depending on test 4.
5. **CI/CD:** instructor demo from mmf-mlops (recommended) — not hands-on.
6. **Deck:** reuse slides from the mmf-mlops Typst deck for an M05 section of the workshop deck (`SPEC_PRESENTATION_TYPST`) — recommended.

## 9. Risks and out of scope

| Risk | Mitigation |
|------|------------|
| Learners may not create jobs or monitors on Vocareum | Test 4; fall back to a run-once notebook and a chart |
| Shocked department too small in the 100-series sample | Test 2; use `daily_train_1000` if needed |
| Champion doesn't visibly drift | The shock is a knob (date, factor); tune it in the dry run |
| mmf-mlops evolves | Port at a recorded commit |

Out of scope: real-time serving; the `AS_OF` live-dashboard cron; rrweb / rehearseur recording; foundation models in the loop (GPU); A/B testing; cost tracking (SPEC_SCALING).

## 10. References

- https://github.com/lbruand-db/mmf-mlops — `SPEC/SPECS.md` (§6 caveats C1–C8, §7 reference architecture), `SPEC/SPECS_HANDSON.md` (§3 arrow of time, revised decision), `SPEC/DEMO_SCENARIO.md`, `demo/README.md`, `demo/resources/jobs.yml`, `demo/src/*`
- `databricks-solutions/mlops-quickstart` (layout followed by mmf-mlops)
- MMF at the pin: `mmf_sa/Forecaster.py` (`evaluate_global_model`, `score_global_model`, `score_local_model`)
- Unity Catalog model aliases: https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle/
- Lakehouse Monitoring: https://docs.databricks.com/aws/en/lakehouse-monitoring/
- Databricks SQL alerts: https://docs.databricks.com/aws/en/sql/user/alerts/
- Course: 3.4 Appendix (registered model naming), 4.2 Appendix (metrics), `SPEC_DEBUGGING.md` (5.3), `SPEC_SCALING.md` (5.4)
