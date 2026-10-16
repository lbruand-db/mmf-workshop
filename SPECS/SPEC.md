# SPEC — Hands-on Workshop: Many-Model Forecasting with Genie Code on M5

| | |
|---|---|
| **Status** | Draft v0.1 — 2026-10-15 |
| **Owner** | Lucas Bruand (Databricks) |
| **Upstream** | [databricks-industry-solutions/many-model-forecasting](https://github.com/databricks-industry-solutions/many-model-forecasting) (MMF, `mmf_sa`, MMF Agent skills) |
| **MLOps extension** | [lbruand-db/mmf-mlops](https://github.com/lbruand-db/mmf-mlops) |
| **First delivery** | Customer workshop, **Tuesday 2026-10-20** |
| **Language** | All material (slides, labs, prompts, instructor notes, course) in **English**; G1 spoken delivery in **French** |

---

## 1. Context and goals

MMF is Databricks' solution accelerator for forecasting thousands of time series in parallel. You configure it rather than code it, using local statistical models, global ML/DL models and foundation models. Since March 2026 it ships as the **MMF Agent**: a set of skills that run inside **Genie Code** (and also Claude Code, Cursor and Copilot) and take a user from a raw table to evaluated forecasts in natural language.

This repository holds **one body of workshop content** that serves three end goals:

| # | End goal | Format | Deadline |
|---|----------|--------|----------|
| **G1** | **Customer workshop**: live, instructor-led, hands-on | ~½ day in a Databricks workspace we prepare | Tue 2026-10-20 |
| **G2** | **MMF course on Vocareum**, packaged through the Vocareum Course Vendor | Self-paced (and optionally instructor-led) lab course with auto-provisioned workspaces | After G1 (target: TBD, see §12) |
| **G3** | **MMF MLOps extra**: taking MMF forecasts to production | Optional add-on module (bonus lab in G1, separate module in G2) | With G2; demo-level for G1 |

**Design principle:** write it once, deliver it twice. Write the labs as Databricks notebooks plus Genie Code prompt scripts that run unchanged in both the customer workspace and a Vocareum-provisioned workspace. Only the environment and setup layer (§7) differs between them.

## 2. Audience and prerequisites

**Primary audience (G1):** Customer data scientists, analytics engineers and demand/supply planners. Expect a mix of coding and low-code participants. Genie Code is the main interface, so participants don't need to write Python.

**Assumed knowledge:**
- Basic Databricks navigation (workspace, notebooks, catalog explorer).
- Basic forecasting vocabulary: horizon, backtest, MAPE/sMAPE/WAPE.
- No prior MMF, MLflow or Spark knowledge required.

**Industry framing:** M5 is retail data (Walmart; item → department → category → store → state). Throughout the workshop we map it to manufacturing and distribution problems: product SKUs × distribution centres / dealers, spare parts, intermittent demand, and hierarchical reconciliation (SKU → product line → brand → region). This keeps the public dataset relevant without using customer data.

## 3. Learning objectives

By the end, participants can:

1. **Explain** the MMF approach: local, global and foundation model classes, backtesting with `backtest_length` and `stride`, and per-series best-model selection.
2. **Install and use** the MMF skill in Genie Code, and drive the full pipeline in natural language while respecting the agent's STOP gates.
3. **Prepare** a many-series dataset (M5) for forecasting: imputation, anomaly capping, exogenous regressors.
4. **Profile** series by forecastability (ADF, STL, spectral entropy, SNR) and choose a strategy for non-forecastable series (include / fallback / separate job).
5. **Run** a multi-model forecast in parallel on Databricks compute, and track it in MLflow.
6. **Evaluate** results: best model per series, WAPE/sMAPE, `forecast_source` provenance, and the MMF Results Explorer app.
7. *(Optional)* **Reconcile** forecasts across a hierarchy (Skill 6).
8. *(G3)* **Operationalise** MMF: scheduled retraining and scoring, model registration in UC, monitoring and promotion.

## 4. Source material and versions

Pin the upstream repo to a commit or tag for each delivery. Record the SHA in `setup/VERSIONS.md`. The skills and `mmf_sa` change often (monthly "What's New" entries).

| Asset | Upstream path | Use in workshop |
|-------|---------------|-----------------|
| MMF skill bundle | `skills/databricks-skills/many-model-forecasting/` (`SKILL.md`, `1-…` to `6-…md`, notebook templates) | Installed into each participant's `/Workspace/Users/{user}/.assistant/skills/` |
| Agent instructions | `skills/assistant_instructions.md` | Installed as `/Workspace/Users/{user}/.assistant_instructions.md`. The `### User Context` section is templated per user |
| M5 data prep | `examples/m5/data_preparation_m5.py` | Basis of our data setup notebook |
| M5 runners | `examples/m5/{local_univariate,global_daily_ml,global_daily_dl,foundation}_daily_m5.py`, `run_daily_m5.py` | Reference solution and "catch-up" path when the agent isn't used |
| Serverless examples | `examples/serverless/*.ipynb` | Default compute path for the workshop (§7.3) |
| Results app | `apps/` (Dash "MMF Results Explorer") | Deployed once per workspace for Lab 5 |
| Hierarchical reconciliation | `mmf_sa` `run_reconciliation_multilevel`, Skill 6 | Optional Lab 6 |
| Fresh Retail Net example | `examples/fresh_retail_net/` (incl. Genie views) | Inspiration for the "Genie on forecasts" segment |
| MLOps | `lbruand-db/mmf-mlops` (`SPEC/`, `demo/`, `deck/`) | G3 module (§9) |

**Runtime:** DBR 18 ML or later, or serverless. All MMF model classes run on serverless since May 2026.

## 5. Dataset: M5

### 5.1 Source
M5 Forecasting (Walmart), loaded via `datasetsforecast==0.0.8` (`M5.load`). It has about 30.5k item-store daily series over about 5.4 years. `df_target` (`unique_id`, `ds`, `y`) is merged with `df_exogenous` (prices, SNAP and event features). `static_features` holds item, dept, cat, store and state.

### 5.2 Tables (per environment: `{catalog}.m5`)

| Table | Content | Purpose |
|-------|---------|---------|
| `daily_train_full` | Full M5, ~30k series | Instructor demo of scale and the G3 MLOps job. **Pre-staged**: the write takes ~45 min |
| `daily_train_1000` | 1,000 sampled series (`random.seed(7)`, as upstream) | **Default participant table** |
| `daily_train_100` | 100 series | Fast path for slow or limited compute, and for Vocareum smoke tests |
| `daily_train_10000` | 10,000 series | Optional "scale it up" exercise |
| `m5_static_features` | Hierarchy attributes per `unique_id` | Profiling breakdowns and Lab 6 reconciliation membership |
| `m5_hierarchy_membership` | Adjacency list (child → parent) for item → dept → cat → store → state | Input to Skill 6 |

Participants **read** from a shared, read-only `{catalog}.m5` schema. They **write** to their own schema `{catalog}.{user_schema}`, so 30 people running the same agent don't collide. The MMF `use_case` prefix (e.g. `m5`) namespaces assets inside a schema.

### 5.3 Forecasting problem (the "forecast problem brief" given to Skill 1)
- Target: daily unit sales per item-store (`y`), frequency `D`.
- Horizon: `prediction_length = 28`, matching the M5 competition.
- Backtest: `backtest_length = 90`, `stride = 7` (as upstream M5 runner); metric sMAPE, with WAPE reported in Skill 5.
- Exogenous: price and SNAP/event flags are available. Skill 1 gate 1.5a lets participants choose whether to use them as dynamic future regressors (default for the workshop: **no**, to save time; **yes** in a bonus exercise).
- Characteristics to discuss: many intermittent / zero-heavy series, which motivates Skill 2 and the Croston/ADIDA/IMAPA/TSB models.

Give participants the brief as copy-paste text, so every room gets the same Skill 1 behaviour.

## 6. Workshop content (shared by G1 and G2)

### 6.1 Agenda for G1 (≈ 3h30 hands-on + breaks; adjust once the slot length is confirmed)

| Time | Module | Format |
|------|--------|--------|
| 0:00–0:20 | **M0 — Intro**: why many-model forecasting; MMF architecture; model classes; MMF Agent and the 5+1 skills; industry use-case mapping | Slides |
| 0:20–0:35 | **Lab 0 — Setup**: open workspace, verify skill install in Genie Code ("What skills do you have access to?"), check catalog/schema | Hands-on |
| 0:35–1:00 | **Lab 1 — Prep & clean** (`/prep-and-clean-data`) on `daily_train_1000` | Hands-on, Genie Code |
| 1:00–1:25 | **Lab 2 — Profile & classify** (`/profile-and-classify-series`, serverless); pick a non-forecastable strategy | Hands-on |
| 1:25–1:35 | Break | |
| 1:35–1:50 | **Lab 3 — Provision** (`/provision-forecasting-resources`); model selection; serverless vs CPU/GPU cluster discussion | Hands-on |
| 1:50–2:30 | **Lab 4 — Execute** (`/execute-mmf-forecast`): jobs run in the background; **instructor fills the wait** with an MLflow tour and a backtesting deep-dive | Hands-on + demo |
| 2:30–3:00 | **Lab 5 — Evaluate** (`/post-process-and-evaluate`); best-model table; Results Explorer app; ask Genie questions about the forecasts | Hands-on |
| 3:00–3:20 | **Lab 6 (optional) / G3 demo — Hierarchical reconciliation** and **MMF MLOps** (scheduled retrain/score, UC models, monitoring) | Demo (+ hands-on for fast finishers) |
| 3:20–3:30 | Wrap-up: mapping to the customer's data, next steps, Q&A | Discussion |

### 6.2 Lab independence principle

**Every lab is self-contained.** A participant can jump to any lab without having completed the preceding ones. This is a hard design constraint, not a nice-to-have: it lets latecomers start mid-session, lets the instructor skip or reorder modules, and lets the Vocareum course offer each module as an independent unit.

How this works in practice:
- Each lab's `catchup.py` is also its **bootstrap**: it materialises all prerequisite tables and assets into the participant's schema. When entering Lab N cold, the participant (or the Vocareum harness) runs Lab N's `catchup.py` first. The notebook is fast (minutes, not the full pipeline) because it writes pre-computed reference results, not re-runs the forecast.
- `checkpoint.py` validates only that lab's outputs — it never checks outputs from earlier labs.
- `prompts.md` includes the Genie Code prompts needed for that lab alone; it does not reference prior conversations.
- Shared read-only tables (`{catalog}.m5.*`) and reference results (`{catalog}.m5_reference.*`) are always available and do not depend on any lab having run.

In short: `catchup.py` is both the fallback for a lab you did and the entry point for a lab you skipped. Every lab starts from a known state.

### 6.3 Lab specification template (per-lab directory)

Every lab directory (`labs/NN-name/`) contains:

- `README.md`: objective, duration, preconditions (tables that must exist), steps, and expected outputs.
- `prompts.md`: **golden-path Genie Code prompts**, plus the expected answer at each STOP gate (e.g. gate `1.0a` → `{catalog}.{user_schema}`; `1.5a` → no dynamic regressors). Participants copy these when unsure. This keeps an LLM-driven lab reproducible.
- `checkpoint.py` (Databricks notebook): **validates** the lab's outputs (tables exist, row counts, schema, at least N models evaluated) and prints PASS/FAIL. The same check is the Vocareum auto-grader (§8.4).
- `catchup.py`: **non-agent fallback** that produces the lab's outputs deterministically by calling `mmf_sa` directly (derived from `examples/m5/*`). A participant who falls behind, or whose agent goes off-track, runs it and continues with the next lab.
- `instructor_notes.md`: talking points, timings, common failure modes.

### 6.4 Per-lab expected outputs

| Lab | Skill | Key gates participants answer | Outputs in `{catalog}.{user_schema}` |
|-----|-------|-------------------------------|--------------------------------------|
| 0 | — | — | Skill visible in Genie Code; schema exists |
| 1 | 1 prep-and-clean | 1.0a catalog/schema, 1.0b brief, imputation, anomaly capping, 1.5a regressors | `m5_train_data` (+ prep reproducibility notebook) |
| 2 | 2 profile (optional) | non-forecastable strategy (A/B/C; workshop default **B, fallback = Seasonal Naive or Zero**) | `m5_series_profile`, `m5_pipeline_config` (+ `m5_train_data_forecastable`) |
| 3 | 3 provision | models, compute | Model list in conversation and config. Default model set below |
| 4 | 4 execute | backtest setup confirmation | `m5_evaluation_output`, `m5_scoring_output`, MLflow experiment, Job runs |
| 5 | 5 post-process | metric and selection rule | `m5_best_models`, `m5_evaluation_summary` (with `forecast_source`) |
| 6 | 6 reconciliation | hierarchy levels | Reconciled forecasts table |

**Default model set for the timed workshop.** It must finish within ~25 min on 1,000 series:
- Local: `StatsForecastBaselineSeasonalNaive`, `StatsForecastAutoETS`, `StatsForecastAutoTheta`, `StatsForecastCrostonOptimized`, `StatsForecastTSB`
- Global ML: MLForecast LightGBM
- Foundation: Chronos-2 or TimesFM 2.5 (see §6.6 for the fast-iteration strategy)

Measure the actual runtime in the dry run (§10) and record it in `instructor_notes.md`.

### 6.5 "Genie on forecasts" segment (Lab 5)

After Skill 5, participants ask natural-language questions of the output tables, either in Genie Code or in a pre-built Genie space over `m5_best_models` / `m5_scoring_output`. Examples: "Which category has the worst WAPE?" and "Which model wins most often for intermittent series?" This shows the planner-facing value. Reuse the pattern in `examples/fresh_retail_net/04_genie_views_setup.ipynb`.

### 6.6 Foundation models and fast iterations

Foundation models (Chronos-2, TimesFM 2.5, Moirai) are a key differentiator of MMF — participants must experience them, not just hear about them. At the same time, GPU runs are slow (cluster startup + inference), and a 30-minute wait kills the learning loop. The strategy below keeps every participant-facing iteration under ~10 minutes while still delivering real foundation model results.

#### Design: split CPU and GPU into parallel tracks

MMF Skill 4 already generates **separate jobs per model class** (one notebook for local, one for global ML, one for GPU models). We exploit this:

```
Lab 4 timeline
──────────────────────────────────────────────────────────────
  Participant kicks off Skill 4
  │
  ├─▶ Job A: local + global ML on serverless CPU (100 or 1,000 series)
  │   └─ finishes in ~5–8 min → participant moves to Lab 5 immediately
  │
  ├─▶ Job B: foundation model on GPU (100 series only)
  │   └─ finishes in ~10–15 min → results appear in evaluation table
  │       while participant is already exploring Lab 5
  │
  └─▶ Reference results (pre-loaded)
      └─ foundation model results on 1,000 series from the dry run,
         already in {catalog}.m5_reference — always available for
         comparison, even if Job B hasn't finished or was skipped
──────────────────────────────────────────────────────────────
```

Participants don't wait for GPU — they continue with Lab 5 on the CPU results and see the foundation model rows appear in their tables as Job B completes.

#### Levers to keep iteration time short

| Lever | Effect | Trade-off |
|-------|--------|-----------|
| **100-series dataset for GPU jobs** | Cuts foundation model runtime from hours to ~10–15 min on a single T4 | Fewer series to compare; mitigated by reference results on 1,000 series |
| **Reduce backtest windows** | `backtest_length=28`, `stride=28` → 1 window instead of ~9 (vs default 90/7). Or `backtest_length=56`, `stride=28` → 2 windows | Fewer backtest points for model selection; acceptable for a learning exercise |
| **Single foundation model** | Run only Chronos-2 **or** TimesFM, not both | Participants see the concept; instructor demos the other on reference results |
| **Pre-warmed GPU cluster** | Start the `g4dn.xlarge` cluster during Lab 2/3, before Lab 4 needs it. Instructor triggers this, or `lab_setup.sh` does it automatically | Costs ~$1/h idle; saves 5–7 min cluster startup |
| **Pre-computed reference results** | Full foundation model backtest on 1,000 series (all models) pre-loaded in `{catalog}.m5_reference` | Always available for Lab 5 exploration and "Genie on forecasts", regardless of what the participant ran |
| **Serverless GPU (AI Runtime)** | If available: no cluster startup, pay-per-use, ~0 wait. This is the ideal path | Region-dependent (preview); confirm in dry run |

#### Recommended configurations by delivery

| Delivery | Dataset for GPU | Backtest config | Foundation model | Cluster strategy |
|----------|-----------------|-----------------|------------------|------------------|
| **G1 (instructor-led)** | 100 series | `backtest_length=56, stride=28` (2 windows) | Chronos-2 on T4 (`g4dn.xlarge`) | Pre-warm during Lab 2; or serverless GPU if available |
| **G2 (Vocareum self-paced)** | 100 series | `backtest_length=28, stride=28` (1 window) | Chronos-2 on T4, time-budgeted | Auto-start in `lab_setup.sh`; auto-terminate 15 min idle |
| **G2 no-GPU fallback** | N/A | N/A | Skip — use reference results only | No GPU cluster; foundation explored via pre-loaded tables |

#### What participants see in Lab 5

Regardless of which path ran, the evaluation and best-model tables contain results from **all model classes**:
- Rows the participant produced (local, global ML, and possibly foundation) carry their `run_id`.
- Pre-loaded reference rows (foundation on 1,000 series) carry `run_id = 'reference'`.
- Lab 5's `prompts.md` includes questions that compare statistical vs foundation models ("For which series does Chronos beat AutoETS?"), so participants always engage with foundation model results even if they didn't run them.

#### Runtime targets (to validate in dry run)

| Model class | Dataset | Backtest | Target runtime | Compute |
|-------------|---------|----------|----------------|---------|
| Local (5 models) | 1,000 series | 90/7 | < 5 min | Serverless CPU |
| Global ML (LightGBM) | 1,000 series | 90/7 | < 3 min | Serverless CPU |
| Chronos-2 | 100 series | 56/28 | < 12 min | `g4dn.xlarge` (T4) |
| Chronos-2 | 100 series | 28/28 | < 8 min | `g4dn.xlarge` (T4) |
| TimesFM 2.5 | 100 series | 56/28 | < 10 min | `g4dn.xlarge` (T4) |

Record actual runtimes in the dry run (§10) and adjust the backtest config if any target is missed.

## 7. Environment and provisioning

### 7.1 Shared requirements (both deliveries)
- Unity Catalog workspace with **Genie Code enabled**, and serverless notebooks/jobs enabled.
- Catalog `mmf_workshop` (name configurable) with a read-only `m5` schema and one writable schema per participant (`u_<shortname>`).
- MMF skill bundle and `.assistant_instructions.md` installed **per user** (Genie Code reads from the user folder; the dots and paths are significant). The `### User Context` block is filled with that user's workspace URL and email.
- Python dependencies: `mmf_sa[local,global,foundation]` from the pinned git SHA. Pre-install on cluster policies / serverless environment where possible, to avoid a 30-person `%pip` storm.
- Spark configs for classic clusters: `spark.sql.execution.arrow.enabled true`, `spark.sql.adaptive.enabled false`.
- MMF Results Explorer app deployed once, with SQL warehouse resource `sql-warehouse`, and `SELECT` on participant schemas granted to its service principal.
- Pre-computed **reference results** in `{catalog}.m5_reference` (full output of Labs 1–6 on `daily_train_1000`, plus a full-M5 run). Used for demos, catch-up and when GPU is unavailable.

### 7.2 Setup automation (`setup/`)
- `setup/workspace_setup.py` (Vocareum `workspace_setup`): creates the shared catalog and schema, stages the pinned skill bundle in a volume, runs the data load (`00_data_load.py`) and reference results (`01_precompute_foundation.py`), and grants learners read-only access.
- `setup/user_setup.py` (Vocareum `user_setup`): for each user (one, or a comma-separated list for G1), imports the skill bundle and the templated instructions file into their home folder through the Workspace API. Idempotent (`overwrite`).
- `setup/02_validate_env.py`: smoke test as a participant. Checks the skill is visible, the data is readable, the schema is writable, and Lab 1 `catchup.py` runs end-to-end on `daily_train_100`.
- Optionally package setup as a **Databricks Asset Bundle** (`databricks.yml`), so the same deploy works for the customer workspace and the Vocareum template workspace.

### 7.3 Compute strategy
- **Default: serverless** for notebooks, profiling and MMF jobs. There's no cluster start-up wait and no quota planning per participant.
- **GPU** (foundation/DL models): confirm availability and quota in the target workspace. If GPU isn't available, foundation and DL models become an instructor demo on reference results.
- Concurrency budget: N participants × (1 profiling run + up to 3 model-class jobs). Validate workspace job and serverless limits for N = expected headcount + 20%.

## 8. Deliverable G2 — Vocareum course (via the Vocareum Course Vendor)

### 8.1 Course structure
Self-paced conversion of §6. Target ~4 h of learner time:
1. Module 1: MMF concepts (video/slides + quiz)
2. Module 2: Genie Code and the MMF Agent (Lab 0)
3. Module 3: Data prep and profiling (Labs 1–2)
4. Module 4: Forecast execution (Labs 3–4)
5. Module 5: Evaluation and business consumption (Lab 5)
6. Module 6 (elective): Hierarchical reconciliation (Lab 6)
7. Module 7 (elective): MMF MLOps (G3, §9)

### 8.2 Self-paced adaptations
- No instructor fills the Lab 4 wait. Default to `daily_train_100` and the CPU-only model set, so jobs finish in < 10 min, and add a reading/MLflow exploration task during the run.
- Every gate decision in `prompts.md` gets a short "why", because there's no instructor to explain it.
- `catchup.py` is surfaced as an explicit "Reset / skip this lab" button or cell.

### 8.3 Lab environment
- One Databricks workspace (or user + schema) per learner, provisioned by Vocareum from a **template** built with the same `setup/` automation (bundle-deployable).
- On learner start, Vocareum's `user_setup` runs `setup/user_setup.py` for that learner. Outputs go to the learner's managed catalog, so no schema creation is needed. The read-only M5 data and reference results are shared and pre-loaded.
- Session limits: time-boxed lab sessions, with idle compute auto-terminated. Model sets are restricted via cluster policies, or serverless budget policies, to control cost.

### 8.4 Assessment
- Each lab's `checkpoint.py` exits with machine-readable JSON (`status` PASS/FAIL plus per-check details). `setup/autograde.py`, the Vocareum `autograde` entry, runs them for the submitting learner and writes the `rubric` / `score` / `feedback` table Vocareum reads.
- Module quizzes cover the concepts in §3 objectives 1, 4 and 6.
- Completion requires Labs 0–5 PASS.

### 8.5 Packaging for the Course Vendor
- Deliverables: lab notebooks (`.py` source format), learner instructions (Markdown), environment template/bundle, grader scripts, slide deck, instructor guide, and a pinned `VERSIONS.md`.
- A content update process for when upstream MMF or the skills change: re-pin the SHA, re-run `02_validate_env.py`, and re-record any videos affected by skill/gate changes.
- *Open:* exact Vocareum Course Vendor packaging format, workspace provisioning model (per-learner workspace vs shared workspace with per-learner schema), and the Genie Code availability on Vocareum-provisioned workspaces. See §12.

## 9. Deliverable G3 — MMF MLOps extra

> **Note:** the contents of `lbruand-db/mmf-mlops` (`SPEC/`, `demo/`, `deck/`) haven't been reviewed for this draft. Align this section with that repo's SPEC and demo before G2. The scope below is the intended target.

**Goal:** show how a one-off agent-driven MMF exploration turns into a governed, recurring production forecast.

**Content:**
1. **From notebooks to a job.** Turn the agent-generated notebooks (Skill 4 orchestrator and run notebooks) into a Lakeflow Job / Asset Bundle with parameters (`run_id`, catalog, schema, model list). Run training/backtest and scoring as separate tasks.
2. **Model management.** Use `run_forecast(model_output=…)` for global/foundation models registered in Unity Catalog. Use MLflow experiment lineage and `run_id` tracking, plus champion/challenger aliases per model class.
3. **Scheduled scoring and retraining.** Rolling weekly re-score; periodic re-backtest and re-selection of best models per series, writing to versioned `best_models` / `scoring_output` tables.
4. **Monitoring.** Forecast accuracy drift (realised vs forecast WAPE per series and segment), data quality alerts (MMF `data_quality_check`), and a dashboard / alert on degradation.
5. **CI/CD.** Dev → staging → prod targets in the bundle; validation of the pinned `mmf_sa` version.
6. **Consumption.** Genie space and/or Results Explorer app on production tables; optional Lakebase serving for planner apps.

**Delivery in G1:** a 10-minute demo on the full-M5 reference run (scheduled job, UC-registered models, monitoring dashboard).
**Delivery in G2:** elective Module 7, with a hands-on lab that deploys the bundle into the learner's schema and runs one scoring cycle, plus a `checkpoint.py`.

## 10. Plan to Tuesday 2026-10-20 (G1)

| Day | Task |
|-----|------|
| Thu 15 | Spec (this doc); confirm open questions with the customer contact (§12); request workspace + Genie Code + GPU |
| Fri 16 | `setup/` scripts; load M5 tables and reference results; pin the MMF SHA |
| Sat 17–Sun 18 | Labs 0–5: `prompts.md`, `checkpoint.py`, `catchup.py`; slide deck (intro + industry mapping) |
| Mon 19 | **Full dry run** as a test participant on the target workspace (time each lab; trial 3–5 concurrent users); deploy the Results Explorer app; finalise instructor notes; G3 demo ready |
| Tue 20 | Delivery. Pre-flight 1 h before: run `02_validate_env.py` for every participant |

Scope for G1 if time is short: Labs 0–5 are must-have; Lab 6 and G3 are demo-only.

## 11. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Agent non-determinism (Genie Code skips or batches gates, generates different code) | Golden-path `prompts.md`; `checkpoint.py` after each lab; `catchup.py` fallback; pinned skill version |
| Genie Code not enabled or skills not picked up (path-sensitive install) | `01_install_skills.sh` + `02_validate_env.py`; verify a day before; fallback: run the `catchup.py` notebooks with the instructor narrating the agent flow |
| Long job runtimes / queueing with many concurrent participants | Serverless default; 1,000 (or 100) series; CPU model set; reference results for demos |
| No GPU quota | Foundation/DL models as demo on pre-computed results |
| Upstream MMF changes break labs | Pin SHA; re-validate before each delivery |
| Customer network / SSO issues on the day | Get access confirmed early; have a Databricks-hosted backup workspace with participant accounts ready |
| Writes colliding across participants | Per-user schemas plus `use_case` prefix; read-only shared data |

## 12. Open questions

1. **Customer workshop:** headcount, exact slot length, onsite vs remote, and their workspace vs a Databricks-provided one. Is Genie Code enabled there? GPU/serverless availability?
2. **Customer workshop:** do they want a "bring your own data" segment, e.g. running Skill 1 on a customer table at the end?
3. **Vocareum:** packaging format and onboarding steps with the Course Vendor; provisioning model; Genie Code support in provisioned workspaces; target publication date; pricing/cost caps per learner.
4. **G3:** confirm the scope against `mmf-mlops/SPEC`, and whether the MLOps demo reuses its `demo/` assets as-is.
5. Should the course also cover Claude Code / Cursor + ai-dev-kit MCP (Option B install), or Genie Code only?

## 13. Acceptance criteria

- **G1:** A test participant completes Labs 0–5 on the target workspace within the agenda timings, using only Genie Code and `prompts.md`. All `checkpoint.py` checks PASS. `catchup.py` recovers from any lab. `02_validate_env.py` passes for every participant account the morning of the session.
- **G2:** A fresh Vocareum-provisioned learner environment passes `02_validate_env.py` with no manual steps. Labs 0–5 auto-grade correctly (PASS on reference solution, FAIL on an empty schema). The package is accepted by the Course Vendor.
- **G3:** The bundle deploys and runs one scheduled scoring cycle on full M5 in a clean schema. The monitoring dashboard shows realised-vs-forecast accuracy. The lab checkpoint PASSes.

## 14. Proposed repository layout

```
mmf-workshop/
├── SPECS/SPEC.md                 # this document
├── setup/                        # admin + per-user provisioning (G1 and G2)
│   ├── VERSIONS.md
│   ├── participants.csv
│   ├── 00_admin_setup.py
│   ├── 01_install_skills.sh
│   ├── 02_validate_env.py
│   └── databricks.yml            # optional bundle
├── labs/
│   ├── 00-setup/ … 06-reconciliation/   # README, prompts, checkpoint, catchup, instructor_notes
│   └── 07-mlops/                 # G3
├── slides/                       # intro deck, industry mapping, MLOps deck
└── vocareum/                     # course-vendor packaging, grader wiring, learner instructions
```
