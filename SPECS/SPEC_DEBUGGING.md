# SPEC — Debugging MMF: Common Failures, Logs, and the Results Explorer

| | |
|---|---|
| **TODO item** | `- [ ] Let's add a lesson on debugging (include something on the https://github.com/databricks-industry-solutions/many-model-forecasting/tree/main/apps MMF results explorer )` |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | **M05 · 5.3 Appendix** — Debugging MMF and the Results Explorer (optional; part of M05 "Running MMF in Production" module) |
| **Type / time** | Appendix / interactive exploration; optional, self-paced; ~20 min |
| **Compute** | Serverless SQL (SQL queries); Databricks Apps (Results Explorer, deployment TBD) |

## 1. Goal and learner outcomes

Equip learners to diagnose and fix common MMF failures during and after forecast runs, and to explore results systematically using logs, MLflow, and the MMF Results Explorer app.

**Learner outcomes:**
- Identify and resolve common data quality failures (missing series, gaps, NULLs, short histories).
- Diagnose model training failures (memory, Spark session issues, incompatible regressors).
- Read MMF logs in the notebook output and MLflow to trace failures to root cause.
- Use the MMF Results Explorer app (Databricks App) to browse, filter, and compare evaluation results.
- Understand the `forecast_source` column (which model produced each forecast) and use it to spot systematic failures (e.g., all intermittent series failed in LightGBM).

## 2. Background — what MMF supports (verified, with source refs)

**Data Quality Checks:**
- MMF runs `DataQualityChecks` (`mmf_sa/data_quality_checks.py`) before modeling if `data_quality_check=True`. It validates:
  - **Minimum length:** Each series must have at least `train_predict_ratio × prediction_length` observations (default `train_predict_ratio=2`).
  - **Gaps in time:** Missing dates are either filled (if `resample=True`, backfilled with 0) or the series is dropped (default `resample=False`).
  - **NULLs in target:** Rows with NULL `y` are dropped.
  - **Constant series:** Series with zero variance are dropped (no meaningful pattern to learn).
  - **Intermittent / sparse series:** No explicit removal, but handled by model selection (e.g., Croston for sparse data).
  - **Output:** `n_forecastable`, `n_non_forecastable` counts in pipeline config; removed series are logged but not explicitly persisted for learner review.

**Model Training Failures (from Forecaster.py):**
- **Local models (statsforecast):** Failures are caught per-series in `applyInPandas` (line 272 of Forecaster.py). If a series fails, the row is dropped from `evaluation_output` and an error is logged. Learners see "`evaluation_output` has fewer rows than input" as a symptom.
- **Global models (LightGBM, NeuralForecast):** Trained once on all series; failures are global. Common causes:
  - **Incompatible regressors:** Future regressors with NULLs, mismatched frequency, or missing future dates → the model can't initialize and the entire job fails.
  - **Memory limits:** On serverless, if the model is too large for the worker's memory, the Spark task fails.
  - **Spark session issues:** Shuffling very large data with small `shuffle_partitions` causes task failures or timeouts.
- **Foundation models (Chronos, TimesFM):** Require GPU; on serverless CPU they fail with "no GPU available" unless caught and skipped.

**Logging & MLflow:**
- MMF logs to MLflow under the `experiment_path` (e.g. `/Users/{email}/mmf_m5_workshop`). Each model/series combination logs metrics (`smape`, `mae`, etc.), parameters, and a `run_id` tag linking back to the main forecast run.
- Standard notebook logs (`logging.getLogger("mmf_sa.*")`) appear in the notebook's Run Details → Logs tab, with INFO / WARNING / ERROR levels.
- Spark task failures log to the cluster's Event Log and Spark History Server (Databricks UI → Compute → cluster name → Event Log tab).

**Results Explorer App (`apps/app.py`, `apps/app.yaml`):**
- A Dash web app that queries `evaluation_output` and `scoring_output` tables.
- **Inputs:** Catalog, schema, table names, optional Run ID filter.
- **Outputs:** Interactive tables and charts:
  - Per-model breakdown: count of series per model, success rate, median metric.
  - Per-series breakdown: forecast, actual, metric, forecast_source, errors.
  - Time series view: forecast vs actual over the horizon for a selected series.
  - Filtering: by series, model, run_id, metric threshold.
- **Deployment:** Requires a SQL warehouse resource key in the app manifest (`app.yaml`). App needs `CAN USE` on warehouse + `SELECT` on tables (SP-based permissions).
- **Learner visibility:** Results Explorer is deployed once per workspace (instructor or learner with admin permissions) and accessible to all learners in the workspace.

**Not yet supported (as of May 2026):**
- Detailed error messages persisted in Delta tables (errors are logged to stdout/MLflow tags, not easily queryable).
- Automated failure classification (e.g., "N series failed due to data quality, M due to model incompatibility").
- Rollback or recovery mechanisms (learners must restart the job).

## 3. Proposed content (section-by-section outline)

### M05 · 5.3 Appendix — Debugging MMF and the Results Explorer

#### Overview (2 min, markdown)
- The debugging workflow: "Something went wrong. Where do I look?"
- Scope: This appendix covers forecast execution failures (data quality, model training, data loading). It is not a deep dive into forecasting theory or statistical troubleshooting (e.g., "why is sMAPE so high?").

#### A. Before you run: data quality checks (5 min, markdown + lab code)
- Show a checklist: **Does your data have…?**
  - All required columns (`unique_id`, date, target, any regressors)?
  - Non-NULL target values?
  - Enough history (at least `train_predict_ratio × prediction_length` rows per series)?
  - No huge gaps (missing dates)?
  - A reasonable range of values (e.g., not all zeros)?
- Learners write a short SQL query to validate their input table before calling `run_forecast`:
  ```sql
  SELECT unique_id, COUNT(*) as n_rows, MIN(y) as min_y, MAX(y) as max_y,
         COUNTIF(y IS NULL) as nulls
  FROM {table}
  GROUP BY unique_id
  ORDER BY n_rows
  ```
- Collapsible ANSWER block: shows how to interpret the output (short series, negative values, all NULLs).

#### B. During execution: reading logs (5 min, live walk-through)
- Show a screenshot of a notebook run with logs:
  - **Notebook output cells:** MMF prints progress ("Computing evaluation for model X…"). Learners scroll to find the last message before an error.
  - **Spark logs (Cluster Event Log):** For Spark task failures, the Compute tab shows which executor failed and why (OutOfMemory, TimeoutException, etc.).
  - **MLflow:** Open the experiment in Databricks UI; each run is logged. Click on a run to see parameters, metrics, and logs (MLflow's built-in Run Details pane).
- Learners do not run a failing job (too time-consuming); instead, they analyze a pre-recorded failure scenario provided as a screenshot + transcript.

#### C. After the run: diagnosing incomplete results (8 min, SQL + Results Explorer)
- **Symptom 1: Fewer rows than expected in `evaluation_output`.**
  - Query to diagnose:
    ```sql
    SELECT model, COUNT(*) as n_series FROM evaluation_output
    GROUP BY model ORDER BY n_series
    ```
  - If one model has far fewer rows, that model failed on many series. Cause: incompatible regressors (LightGBM with NULLs), or the model class itself is broken.
  - **Resolution:** Check model-specific issues (e.g., LightGBM requires no NULLs in X; verify your regressors).

- **Symptom 2: A subset of `unique_id` values are missing from results.**
  - These series hit data quality checks and were removed.
  - Query to find them:
    ```sql
    SELECT DISTINCT unique_id FROM {train_table}
    EXCEPT
    SELECT DISTINCT unique_id FROM evaluation_output
    ```
  - Check the removed series in the input table: too short, all NULLs, constant, etc.
  - **Resolution:** Increase `train_predict_ratio`, impute NULLs, or segment analysis by series length.

- **Symptom 3: Foundation model results are missing (no Chronos rows).**
  - On serverless CPU, foundation models silently fail (no GPU). Results Explorer shows only local + global.
  - **Resolution:** Use pre-computed reference results (included with the workshop) or provision GPU (instructor-led).

#### D. Exploring results with the MMF Results Explorer (5 min, interactive demo)
- **App deployment:** Show a screenshot of the Results Explorer deployed in the workspace (e.g. at `https://<workspace>.databricksapps.com/mmf-app`).
- **Usage walkthrough:**
  - Input: catalog, schema, evaluation_output table name.
  - Browse table: displays all rows (capped at 10k); filter by model, series, or run_id.
  - Per-model summary: card view showing model name, count, median metric.
  - Time series view: select a series and see forecast vs actual as a line chart.
  - Hover to see forecast_source (which model produced the forecast for this series).
- **Learner task:** Reproduce the walk-through with reference results provided by Classroom-Setup-4.3; take a screenshot of a specific series's forecast (e.g., the best and worst by sMAPE).
- **Collapsible ANSWER block:** Shows a sample time series view and how to interpret the forecast quality visually.

#### E. Summary: troubleshooting decision tree (3 min, diagram)
- **Flowchart (ASCII or inline SVG):**
  ```
  Does evaluation_output have results?
  ├─ NO → Check notebook logs for Spark errors
  │        (Task failed, out of memory, timeout)
  │
  ├─ YES, but too few rows
  │   ├─ One model has few → Check model-specific logs (regressors, NULLs)
  │   └─ All models low → Data quality issue (check series count, length)
  │
  ├─ YES, looks complete
  │   └─ Use Results Explorer to browse results
  │       (Check forecast_source, time series view, compare models)
  ```
- Learners reference this when troubleshooting their own runs.

#### F. (Optional) Interpreting `forecast_source` and provenance (2 min, concept)
- The `forecast_source` column in `evaluation_output` (or output from Skill 5) indicates which model produced the best forecast for each series.
- If a particular model is the `forecast_source` for all series, it's likely the strongest; if none, an ensemble or fallback was used.
- Use this to spot patterns: e.g., "LightGBM is best for series with high variance; local models for short, sparse series."

### Classroom Setup (Includes/Classroom-Setup-4.3.py)
- Copies M04 reference results (best_models, evaluation_output, scoring_output) to learner schema.
- Ensures Results Explorer can be deployed (SQL warehouse is available).

## 4. Interactive / visual component (if any)

**M05 · 5.3:**
- **Decision tree flowchart** (section E): ASCII or inline SVG, embedded in markdown cell.
- **Screenshots:** Provided as images in markdown cells (notebook logs, Spark Event Log, MLflow Run Details, Results Explorer demo).
- **Results Explorer app:** Live Databricks App (already built upstream; linked in the lesson).

## 5. Data, setup and runtime

**Data inputs:**
- `mmf.m5_reference.evaluation_output` (from M03 or pre-computed setup) — provides realistic results for exploration.
- `mmf.m5_reference.scoring_output` (same).

**Outputs:**
- Learner screenshots / responses (informal; stored in cell outputs, not persisted).

**Runtime:**
- No Spark jobs. All queries are fast SQL on cached reference data.
- Results Explorer loads in seconds (Dash app, ~100k rows typical).

**Compute:**
- SQL warehouse for Results Explorer (shared, no provisioning needed).
- Serverless notebook compute for SQL cells (one-shot, no concurrency).

## 6. Files to create / change

**Notebooks:**
- `labs/Source/en_us/notebooks/M05 - Running MMF in Production/5.3 Appendix - Debugging MMF and the Results Explorer.py`
- `labs/Source/en_us/notebooks/Includes/Classroom-Setup-5.3.py`

**Supporting images/diagrams:**
- `labs/Source/en_us/notebooks/Includes/images/decision_tree_debugging.svg` (ASCII diagram or SVG)
- Screenshots (stored as image files or inline in markdown):
  - `notebook_logs_example.png`
  - `spark_event_log_example.png`
  - `mlflow_run_details.png`
  - `results_explorer_demo.png`

**Supporting code (optional):**
- `labs/Source/en_us/notebooks/Includes/_debugging_helpers.py` (optional: SQL templates for diagnostics, common queries)

**Apps:**
- No new apps. Reference the existing `apps/app.py` (MMF Results Explorer) from upstream. Instructions for deploying it per workspace (in Classroom-Setup or an admin guide).

## 7. Test plan (e2-demo and/or Vocareum)

**e2-demo (instructor-only):**
1. Run M04 forecast (or use reference results).
2. Enter M05 · 5.3 cold (Classroom-Setup-5.3 copies results).
3. Complete section A: verify the data quality query runs and returns sensible output.
4. Review section B: screenshots of logs are readable and relevant.
5. Complete section C: run the diagnostic SQL queries; confirm they identify missing series / models correctly.
6. Section D (Results Explorer): IF deployment succeeds (per D3 decision), verify the app loads and filters work. ELSE, confirm fallback (static screenshots) is provided.
7. Complete section E: follow the decision tree on reference data (should show "YES, looks complete" path).

**Vocareum (learner-paced, G2):**
1. Enter M05 · 5.3 cold.
2. Sections A–B are markdown + reading (no execution).
3. Section C: run SQL diagnostic queries (fast, cached data).
4. Section D: access Results Explorer via browser (link provided) IF deployed; otherwise view static screenshots provided. Take screenshots if interactive.
5. (Optional) Skip section F (concept-only).

**Timing:**
- Full appendix: 20 min (mostly reading + exploration, no long-running jobs).
- Can be compressed to 10 min for a workshop (sections A–C only, Results Explorer as a demo-only link).

## 8. Decisions for the reviewer (numbered, with a recommended option)

| # | Decision | Options | **Recommended** | Rationale |
|---|----------|---------|-----------------|-----------|
| **D1** | Failure scenario: live or recorded | (a) Provide a transcript + screenshot of a real failed run; learners analyze it. (b) Have learners intentionally break a forecast (bad input) and debug it live. | **(a)** | (b) is unpredictable and time-consuming. (a) is safe, reproducible, and teaches the same skills. |
| **D2** | Data quality checks: show MMF's checks or teach learners to write their own? | (a) Explain MMF's `DataQualityChecks` class; link to source code. (b) Have learners write their own checks (e.g., Spark DataFrame validations). | **(a)** | (a) is practical and doesn't reinvent. Learners understand why their series was removed. (b) is valuable but adds 10 min. |
| **D3** | Results Explorer: live deployment on Vocareum or fallback to screenshots? | (a) Attempt to deploy Results Explorer in Vocareum workspace (instructor or admin); learners access live app. (b) Provide static screenshots of Results Explorer + demo video; learners view only (no interactivity). | **(a) with (b) fallback** | (a) is more engaging. **Caveat: Deployment on Vocareum is unverified.** If R&D testing (§7) shows deployment fails due to app/warehouse/permissions issues, switch to (b) fallback for learners. Instructor retains the ability to deploy on e2-demo. |
| **D4** | Scope: include foundation model failures? | (a) Brief mention: foundation models fail on serverless CPU (no GPU); reference pre-computed results. (b) Deep dive: what happens if learner tries to run Chronos on CPU. | **(a)** | (a) is sufficient. (b) adds confusion and time. Most learners won't run foundation models in a 2-hour workshop. |
| **D5** | Logs deep dive: Spark Event Log or just notebook output? | (a) Focus on notebook output and MLflow; Spark Event Log is optional deepdive. (b) Require learners to find and read Spark Event Logs. | **(a)** | (a) is accessible. Spark Event Log requires cluster admin permissions (Vocareum may restrict). (b) is valuable but optional. |
| **D6** | Diagnosis task: learner does SQL or instructor shows results? | (a) Learners write SQL queries to diagnose (section C lab code). (b) Instructor provides the results; learners interpret. | **(a)** | (a) is active learning and transferable. (b) is faster. (a) + (b) together: provide templates so learners have a scaffolded task. |

## 9. Risks and out of scope

**Risks:**

1. **Results Explorer deployment on Vocareum is unverified:** Databricks Apps may or may not be deployable by learners in Vocareum-managed workspaces. The app requires a SQL warehouse, UC grants, and proper service principal permissions (SP-based). **Mitigation:** Test deployment on the Vocareum test workspace early (phase 6 / R&D testing, §7). If deployment succeeds, use (D3 option a). If it fails, fall back to (D3 option b): static screenshots + demo video (less interactive but universally accessible).

2. **Insufficient troubleshooting scenarios:** The appendix covers common failures, but a learner's unique issue might not be addressed. **Mitigation:** Provide a Q&A link / feedback channel; collect common issues and add them to a "FAQ" section post-workshop.

3. **Learners over-interpret Results Explorer:** Filters and charts can mislead if used carelessly (e.g., filtering to a small subset and drawing conclusions). **Mitigation:** Include a note: "Results Explorer is for exploration and validation, not statistical inference."

**Out of scope:**

- **Statistical troubleshooting** (why is accuracy low?): Covered partially in M04 · 4.2 (metric choice). Deep statistical diagnosis is beyond the workshop scope.
- **Hyperparameter tuning:** Failures due to bad hyperparameters (e.g., LightGBM too deep) are out of scope. Learners should accept defaults and tune post-workshop.
- **Distributed computing failures (Spark, JVM internals):** While Spark errors are mentioned, deep JVM debugging is out of scope.
- **GPU debugging:** Foundation models and GPU issues (CUDA memory, driver crashes) are not covered; learners use pre-computed results.
- **Automated remediation:** Suggesting fixes and re-running jobs is out of scope; learners manually correct input and retry.

## 10. References

- **MMF Data Quality Checks:** `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/data_quality_checks.py`
- **MMF Forecaster (error handling):** `/tmp/mmf_upstream/many-model-forecasting-main/mmf_sa/Forecaster.py` (see exception classes in `mmf_sa/exceptions.py`)
- **MMF Results Explorer:** `/tmp/mmf_upstream/many-model-forecasting-main/apps/` (app.py, app.yaml, README.md)
- **Databricks MLflow UI:** https://docs.databricks.com/en/mlflow/index.html
- **Spark Event Log & Cluster Logs:** https://docs.databricks.com/en/clusters/spark-drivers-executors.html#spark-executor-logs
- **Databricks Compute troubleshooting:** https://docs.databricks.com/en/clusters/troubleshoot.html
- **Lakehouse troubleshooting:** https://docs.databricks.com/en/lakehouse-monitoring/troubleshoot.html
