# SPEC — Operationalizing MMF: Scheduled Retraining, Model Promotion, and Monitoring

| | |
|---|---|
| **TODO item** | `- [ ] Let's add a lesson on MLOps` |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | **M05 · 5.1 Lab** — Scheduled Retraining and Model Promotion; **M05 · 5.2 Appendix** — Monitoring Forecast Accuracy (both optional; part of M05 "Running MMF in Production" module) |
| **Type / time** | Lab + optional Appendix; **optional for G1 & G2** (~45 min core + 30 min monitoring) |
| **Compute** | Serverless CPU (notebooks, Jobs, SQL queries) |

## 1. Goal and learner outcomes

Enable learners to take a trained MMF forecast into production: schedule automatic retraining, manage model versions in Unity Catalog, and monitor forecast accuracy drift over time.

**Learner outcomes:**
- Set up a Databricks Job to retrain an MMF forecast on a schedule and score new data.
- Register trained MMF models in Unity Catalog and use model aliases for version management (e.g., swap `champion` → new challenger version).
- Compare forecast accuracy before and after retraining to detect model drift.
- (Optional, monitoring) Set up simple accuracy tracking: daily/weekly aggregates of actual vs forecast, and trigger alerts on threshold breaches (e.g. sMAPE > 15%).

## 2. Background — what MMF supports (verified, with source refs)

**Model Registration & Lifecycle (verified against Forecaster.py):**
- MMF registers global models (LightGBM, NeuralForecast, Chronos) in UC during `run_forecast` (Forecaster.py lines 383, 502, 738): models are registered under `{model_output}.{model_name}_{use_case_name}` (e.g., `catalog.schema.LightGBMRegressor_m5`). Each retraining creates a new **version**; MMF does not set aliases itself.
- Local models (statsforecast, sktime) are not persisted as registered artifacts — only results (predictions + metrics) are in `evaluation_output` and `scoring_output`. Each retraining cycle retrains local models from scratch.
- Global model pickles are stored in `evaluation_output` as a binary column; they are not automatically reused across runs.

**Scheduling & Jobs:**
- Databricks Jobs support one-time and recurring schedules. They can run notebooks or submit Spark workloads. Since MMF operates via notebooks (Skills or direct `run_forecast` calls), a Job can invoke an MMF notebook on a fixed or cron schedule.
- Multi-task jobs allow sequential steps: e.g., (1) run forecast, (2) register model, (3) score new data, (4) evaluate accuracy drift, all in one job run with conditional transitions.

**Monitoring & Drift Detection:**
- Databricks Lakehouse Monitoring tables allow automatic data drift and model performance tracking if paired with logged predictions (not yet integrated with MMF). A simpler workshop pattern: compute daily/weekly forecast accuracy directly from `evaluation_output` and `scoring_output`, store in a "monitoring" table, and plot over time.
- System tables (`system.billing.usage`, `system.access.audit`) are read-only and require attentive filtering but enable cost tracking and access audits.

**UC Model Registry — aliases and version management:**
- Models registered in UC support **aliases** (named pointers to specific versions). UC does not use "stages" (Development/Staging/Production); instead, use aliases like `champion` (current production model), `challenger` (candidate), `archived`, etc.
- Aliases allow safe promotion: update an alias to point to a new version without changing code that reads the model. All consumers automatically use the new version on refresh.
- Access control is via UC grants (`GRANT USE_MODEL` to users/service principals).

**Not yet supported (as of May 2026):**
- Automated model validation (gating stage transitions on metric thresholds) — learners must evaluate and decide.
- Hierarchical forecasts do not have native retraining-and-reconciliation pipelines; each hierarchy level must retrain and reconcile separately.

## 3. Proposed content (section-by-section outline)

### 3.1 M05 · 5.1 Lab — Scheduled Retraining and Model Promotion

#### Overview & objectives (5 min, markdown)
- Why retraining matters: models degrade as data drifts; forecast accuracy decays over time.
- The retrain-monitor-promote cycle in production: from daily/weekly retraining to controlled promotion.

#### A. Prepare a retraining notebook (10 min, live demo + learner code)
- Given a trained model from M04 and reference data in `mmf.m5`, prepare a notebook that:
  - Re-runs the forecast with the same hyperparameters and horizon (copy from M04 or use a parameter widget).
  - Logs the run to MLflow and extracts the accuracy metrics.
  - Writes results to `{schema}.{use_case}_retraining_log` (a Delta table tracking all retraining runs).
- Classroom setup copies `m5_reference` results so learners can skip M03–M04 and focus on the job/governance layer.

#### B. Create and monitor a Databricks Job (15 min, live walk-through)
- Walk learners through the Databricks Jobs UI:
  - Create a multi-task job: Task 1 = run forecast (invoke the notebook from A); Task 2 = evaluate drift (SQL cell comparing new accuracy to a baseline); Task 3 = conditional notify (e.g. Slack message if sMAPE > 15%).
  - Set a schedule: daily or weekly (learner chooses).
  - Configure compute: serverless or a shared all-purpose cluster (note cost/time trade-offs).
  - Show MLflow integration: results are logged automatically under the job's run.
- **Hands-on:** Learners create their own job (not submit it, just confirm the UI state in a screenshot).

#### C. Register models in Unity Catalog and manage aliases (10 min, lab code)
- MMF has already registered the trained model during `run_forecast`. Inspect the registered model:
  ```python
  from mlflow.tracking import MlflowClient
  client = MlflowClient()
  # List versions of the registered model
  versions = client.search_model_versions(filter_string=f"name='{catalog}.{schema}.LightGBMRegressor_m5'")
  for v in versions:
    print(f"Version {v.version}: {v.status}")
  ```
- Create an alias (e.g., "champion") pointing to the current best version:
  ```python
  client.set_model_alias(
      name=f"{catalog}.{schema}.LightGBMRegressor_m5",
      alias="champion",
      version=version_number
  )
  ```
- Demonstrate alias promotion: when a new version is trained, update the "champion" alias to point to it (old consumers refresh to get the new model).
- Query the UC Model to confirm versions and alias assignments.

#### D. Best practices checkpoint (5 min)
- Collapsible ANSWER block: `<details><summary>How would you automate promotion?</summary>...</details>`
  - Manual approval via Slack button (Future: Databricks Apps with a custom UI).
  - Metric-gated promotion: only promote if `sMAPE < threshold` on the holdout set.
  - Use a Databricks Workflow webhook or an external CI/CD system.

### 3.2 M05 · 5.2 Appendix — Forecast Accuracy Monitoring (optional, 30 min)

#### Overview (2 min, markdown)
- Monitoring vs. retraining: what to watch for in production and how to detect when a model is degrading.
- The monitoring table: simple schema tracking daily/weekly forecast accuracy and data volumes.

#### A. Build a monitoring table (10 min, SQL + Python)
- Query `evaluation_output` and `scoring_output`, compute rolling weekly averages of sMAPE by `unique_id` and `use_case`.
- Store the aggregates in `{schema}.{use_case}_monitoring_log` with columns: `compute_date`, `window_end_date`, `n_series`, `median_smape`, `pct_series_above_threshold` (e.g., % with sMAPE > 20%).
- Learners write the SQL; instructor provides the template.

#### B. Detect drift and visualize trends (10 min, Python + matplotlib chart)
- Plot time series of `median_smape` and alert on sustained increases (e.g., 10%-point jump in 2 weeks).
- Collapsible ANSWER block with a matplotlib figure (static, displayed via Databricks notebook output) and a simple rule: "If rolling 7-day median sMAPE > 1.2 × baseline, flag a retraining.".
- Discuss false positives: seasonal spikes, data quality issues, vs. true model drift.

#### C. (Optional) Lakehouse Monitoring integration preview (5 min, concept)
- Show a screenshot of Databricks Lakehouse Monitoring on the evaluation output table.
- Link to the [official docs](https://docs.databricks.com/en/lakehouse-monitoring/monitor-data.html); learners can enable it in their own workspace after the course.

#### D. Troubleshooting checkpoint (3 min)
- Q: "My forecast accuracy jumped. Is the model broken?" → Check (1) input data quality (same schema? NULLs?), (2) recent retraining (is a new model in Production?), (3) seasonal spike or external event.

## 4. Interactive / visual component (if any)

**M05 · 5.1:**
- No interactive components; learner interacts with the Jobs UI and MLflow.

**M05 · 5.2:**
- Matplotlib chart (static, in a notebook cell output): weekly sMAPE time series with a reference band (baseline ± 10%).
- No interactive widget for M05 · 5.2 (out of scope). A self-contained HTML widget for configurable alert thresholds (similar to 3.1 / 4.2) could be added in a future iteration.

## 5. Data, setup and runtime

**Data inputs:**
- `mmf.m5.daily_train_100` or `daily_train_1000` (same training data as M03–M04).
- `mmf.m5_reference.evaluation_output` (pre-computed reference results for learners who skip M03–M04).

**Outputs:**
- `{user_schema}.m5_retraining_log` (audit table: one row per job run, with run_id, timestamp, sMAPE, version).
- `{user_schema}.m5_monitoring_log` (optional, M05 · 5.2: rolling accuracy aggregates).
- UC Model Registry entries (e.g. `{catalog}.{schema}.m5_forecast` versions 1, 2, …).

**Runtime:**
- Forecast retraining (M05 · 5.1 A): 10–15 min on 100 series (same as M03 fast model set).
- Job setup and registration: 5 min.
- Monitoring setup (M05 · 5.2): 5 min (no Spark jobs; SQL queries on cached results).

**Compute:**
- Serverless SQL warehouse for SQL cells (M05 · 5.2 monitoring queries).
- Serverless notebook compute for the forecast notebook (M05 · 5.1 A).
- Single-machine CPU for model registration (MLflow client).

## 6. Files to create / change

**Notebooks:**
- `labs/Source/en_us/notebooks/M05 - Running MMF in Production/5.1 Lab - Scheduled Retraining and Model Promotion.py`
- `labs/Source/en_us/notebooks/M05 - Running MMF in Production/5.2 Appendix - Monitoring Forecast Accuracy.py`
- `labs/Source/en_us/notebooks/Includes/Classroom-Setup-5.1.py` (copies M04 reference results to learner schema)
- `labs/Source/en_us/notebooks/Includes/Classroom-Setup-5.2.py` (copies retraining log)

**Supporting modules:**
- `labs/Source/en_us/notebooks/Includes/_mlops_helpers.py` (optional: helper functions for model registration, alias management, monitoring SQL templates)

**Upstream reference (informational):**
- Companion repo [lbruand-db/mmf-mlops](https://github.com/lbruand-db/mmf-mlops) (demos, deck, spec) — link in M05 overview but do not copy code (copyright).

## 7. Test plan (e2-demo and/or Vocareum)

**e2-demo (instructor-only):**
1. Run M04 forecast (or import reference results).
2. Run M05 · 5.1 retraining notebook: confirm new models are trained and logged in MLflow.
3. Create a Job in the UI: task 1 = notebook, task 2 = SQL accuracy check. Trigger it manually. Confirm results in `retraining_log`.
4. Register a model in UC, create/update aliases (`champion`, `challenger`). Verify via `mlflow.tracking.MlflowClient().get_model_version_by_alias(…)`.
5. Run M05 · 5.2 monitoring: confirm rolling accuracy aggregates are computed.

**Vocareum (learner-paced, G2):**
1. Enter M05 · 5.1 cold (Classroom-Setup-5.1 copies results from `m5_reference`).
2. Complete A (retraining notebook) and B (Job setup in UI — screenshot task only).
3. Complete C (model registration in UC).
4. (Optional) Skip M05 · 5.2 or include it as a bonus.

**Timing validation:**
- Full M05 (5.1 + 5.2): 75 min.
- Standalone M05 · 5.1: 45 min (sufficient for G1 add-on if time allows).

## 8. Decisions for the reviewer (numbered, with a recommended option)

| # | Decision | Options | **Recommended** | Rationale |
|---|----------|---------|-----------------|-----------|
| **D1** | Scope of model persistence | (a) Only demonstrate model registration in UC; don't extract pickles from `evaluation_output`. (b) Teach learners to extract and deserialize model pickles from the evaluation table and use them for batch scoring. | **(a)** | Extraction is low-level; MMF's native path is to retrain. (b) adds 15 min and obscures the bigger MLOps story. Can link to advanced tutorials. |
| **D2** | Job creation: live UI or notebook API | (a) Walk through the Jobs UI, learners take screenshot. (b) Use the Databricks Python SDK to create a job programmatically in a notebook. | **(a)** | UI is discoverable and visible; API requires SDK familiarity. (b) is valuable for advanced users; offer as optional deepdive. |
| **D3** | Monitoring: simple SQL or Lakehouse Monitoring | (a) Write custom SQL to compute rolling accuracy; optional reference to Lakehouse Monitoring. (b) Require learners to enable Lakehouse Monitoring on the evaluation table. | **(a)** | SQL is transparent and works on any Databricks workspace. Lakehouse Monitoring is a premium feature and adds operational complexity. (a) + optional reference is best. |
| **D4** | Multi-task job with conditional branching | (a) Show a simple linear job: forecast → register model. (b) Build a complex job with conditional tasks (e.g., only promote if sMAPE < 15%). | **(a)** | Linear is clearer. (b) is valuable but requires careful design; defer to G3 / advanced track. |
| **D5** | Include retraining on fresh data vs. same training window | (a) Retrain on the same historical window (deterministic, easier to compare). (b) Simulate forward time: train on Jan–Mar, score on Apr, then retrain on Jan–Apr and score on May. | **(a)** | (a) focuses on the governance and scheduling pattern. (b) is realistic but adds complexity and confusion (what baseline?). Mention as future extension. |
| **D6** | Monitoring: learner-created dashboard or static chart | (a) Provide a static matplotlib chart in a notebook cell (learners see example). (b) Have learners build their own Databricks Dashboard or Lakeview dashboard. | **(a)** | Dashboards are out of scope for this workshop. Static matplotlib chart + guidance is sufficient. Dashboards are valuable but 30 min is tight. |

## 9. Risks and out of scope

**Risks:**

1. **UC Model Registry maturity on Vocareum:** If the managed catalog / metastore setup on Vocareum doesn't allow model registration, M05 · 5.1 C (registration) fails. **Mitigation:** Test model registration (MLflow Python API) on the Vocareum test workspace early. If it fails, adjust to a Workspace Model Registry fallback (less durable but works).

2. **Job scheduling permissions:** Vocareum / learner environments may not allow job creation (admin-only). If so, M05 · 5.1 B becomes a demo-only walkthrough, not a hands-on lab. **Mitigation:** Confirm learner role grants `CAN_ATTACH_TO_CLUSTERS` and `CAN_MANAGE_RUN` in Vocareum setup scripts.

3. **MLflow experiment scope:** M05 · 5.1 A logs to `/Users/{email}/mmf_m5_workshop` (shared with M03–M04). If learners race and collide on MLflow runs, results are confusing. **Mitigation:** Use per-user experiment paths by default.

4. **Scheduling granularity:** Databricks Jobs support cron schedules, but the UI is cumbersome. Manual job triggers are easier for learners; a screenshot-based exercise is realistic.

**Out of scope:**

- **Foundation models in production:** GPU scheduling and licensing complexity; learners should use pre-computed results.
- **A/B testing frameworks:** Beyond the scope of a 2-hour workshop; mention as future extension.
- **Hierarchical reconciliation + retraining:** Skill 6 reconciliation is optional; integrating it with retraining (e.g., retrain each level, then reconcile) is a G3 advanced topic.
- **Fine-grained access control:** UC grants are mentioned but not deeply explored. Link to docs.
- **Cost optimization:** Tracking job costs via `system.billing.usage` is valuable but adds SQL complexity. Optional deepdive.
- **Automated promotion gating:** Metric-based stage transitions require external CI/CD or serverless functions; out of scope for this workshop.

## 10. References

- **Databricks MLflow Model Registry:** https://docs.databricks.com/en/mlflow/model-registry/index.html
- **Databricks Jobs API & scheduling:** https://docs.databricks.com/en/workflows/jobs/index.html
- **Unity Catalog models:** https://docs.databricks.com/en/model-registry/index.html
- **Lakehouse Monitoring:** https://docs.databricks.com/en/lakehouse-monitoring/monitor-data.html
- **MMF Skills:** `/tmp/mmf_upstream/many-model-forecasting-main/skills/` (Skill 1–6 in repo; Skill 5 handles post-processing)
- **Companion repo (mmf-mlops):** https://github.com/lbruand-db/mmf-mlops (demo, deck, SPEC — referenced but not copied)
- **System tables (billing, access):** https://docs.databricks.com/en/admin/system-tables/index.html
