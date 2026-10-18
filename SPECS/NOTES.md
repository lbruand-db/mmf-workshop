# Working Notes

## 2026-10-15 — Vocareum Course Vendor instance

An example course has been created on Vocareum using the Databricks Course Vendor app:

- **Course Vendor URL:** <https://vocareum-course-vendor-prod-7474657511257498.aws.databricksapps.com/>
- **Databricks workspace:** <https://dbc-698fdf17-083d.cloud.databricks.com/>

This is the environment to test the Vocareum packaging and provisioning flow described in `VOCAREUM.md`.

## 2026-10-15 — Workspace reconnaissance and risk mitigation

**Profile:** `mmf-workshop` (PAT auth as `adminuser3540596@vocareum.com`, admin role).

### Findings

| Check | Status | Detail |
|-------|--------|--------|
| CLI | OK | v1.18.0 |
| Auth | OK | PAT, admin user on workspace |
| Cloud | AWS | Confirmed from cluster policies and workspace config |
| Unity Catalog | OK | Catalogs: `dbacademy`, `main`, `samples`, `system`. Created `mmf` catalog + `mmf.m5` schema |
| SQL Warehouses | OK | 2 warehouses (both PRO, serverless-enabled, currently stopped): one personal, one shared (`shared_warehouse`, max 4 clusters) |
| Serverless compute | OK | `enable_serverless_compute: true` on warehouse config |
| Cluster policies | OK | 5 policies: Personal Compute, Power User, Shared, Job, Legacy Shared |
| **GPU availability** | **OK** | `g4dn.xlarge` (1× T4, 16 GB VRAM) is in the **Personal Compute** policy allowlist alongside `i3.xlarge/2xlarge/4xlarge` and `i3en.xlarge` |
| Job Compute policy | OK | `node_type_id` is unlimited (not restricted) — GPU instances can be used for jobs too |
| Genie Code skills | **Installed** | MMF skill bundle (15 files) uploaded to `/Users/adminuser3540596@vocareum.com/.assistant/skills/`; `.assistant_instructions.md` uploaded |
| Existing data | Empty | `dbacademy.ops.meta` has one table; lab user schema is empty; `mmf.m5` just created |
| Recent jobs | None | No job runs yet |

### Risk mitigation status (vs SPEC.md §11)

| Risk | Status | Action taken / remaining |
|------|--------|--------------------------|
| **Agent non-determinism** | Mitigated (design) | `prompts.md` + `checkpoint.py` + `catchup.py` per lab — to be built |
| **Genie Code not enabled / skills not picked up** | **Partially mitigated** | Skill bundle installed for admin user. Need to test in browser that Genie Code sees it ("What skills do you have access to?"). Cannot verify from CLI alone |
| **Long job runtimes** | Mitigated (plan) | Will use `daily_train_100` or `daily_train_1000`. CPU model set default. Need M5 data load |
| **No GPU quota** | **BLOCKER** | `g4dn.xlarge` is allowlisted in policy but AWS account has no GPU EC2 quota (`AWS_RESOURCE_QUOTA_EXCEEDED`). Serverless GPU (`hardware_accelerator: GPU_1xA10`) silently ignored — not enabled on this workspace. **Workaround:** pre-compute Chronos-2 results on CPU and store as `mmf.m5.reference_*` tables. See §below |
| **Upstream MMF changes** | Not yet mitigated | Need to pin SHA in `setup/VERSIONS.md` |
| **Network/SSO issues** | N/A for Vocareum | Vocareum handles learner access |
| **Write collisions** | Mitigated (plan) | Per-user schemas. `mmf` catalog + `m5` shared schema created. Need per-user schemas at setup time |
| **Serverless** | **Confirmed** | Serverless is enabled on the workspace. SQL warehouses are serverless-capable (PRO type) |

### GPU status (2026-10-15)

**No GPU access on Vocareum workspace.** Two paths tested, both failed:

1. **Classic GPU cluster** (`g4dn.xlarge`): `AWS_RESOURCE_QUOTA_EXCEEDED` — the Vocareum AWS account has zero GPU EC2 instance quota.
2. **Serverless GPU** (`hardware_accelerator: GPU_1xA10`): field silently ignored by the API — serverless GPU is not enabled on this workspace.

**Workaround:** pre-compute foundation model results on CPU (`setup/01_precompute_foundation.py`) and store them in `mmf.m5.reference_evaluation_output` and `mmf.m5.reference_scoring_output`. Participants see real Chronos-2 results in Lab 5 without needing GPU.

~~**To fix properly:** ask Vocareum to either (a) increase the AWS GPU instance quota for g4dn.xlarge, or (b) enable serverless GPU (AI Runtime) on the workspace.~~ *Superseded 2026-10-16:* the L&E Vocareum guidelines forbid GPUs in labs, so pre-computed reference results are the intended design, not a workaround.

### Next steps to complete risk mitigation

1. ~~**Load M5 data** into `mmf.m5`~~ — DONE: `daily_train_100`, `daily_train_1000`, `m5_static_features`
2. ~~**Test Lab 4 (CPU)**~~ — DONE: 6 models × 100 series, 891 eval rows each
3. ~~**Test Lab 5**~~ — DONE: best-model selection works, 99 series ranked
4. ~~**Pre-compute foundation results**~~ — DONE: ChronosBoltSmall on CPU, 200 eval rows (Chronos-2 was replaced by Bolt-Small)
5. **Test Genie Code** in the browser — verify the skill is visible
6. **Run a full Lab 1–5 dry run** as a participant to time everything
7. **Pin the MMF SHA** and record it
8. **Create a test learner schema** (`mmf.u_testuser`) and verify permissions
9. ~~**Build the Vocareum setup scripts**~~ — DONE 2026-10-16 as `.cfg` hooks (`setup/workspace_setup`, `user_setup`, `autograde`) plus `vocareum/` packaging; see below

## 2026-10-16 — Review against L&E Vocareum guidelines

Reviewed the labs against go/field-driven-enablement-labs, go/vocareum-lab-guidelines and go/vocareum-lab-development (summarised in `VOCAREUM.md`). What changed as a result:

| Finding | Change |
|---------|--------|
| Each workspace has its own metastore; shared data was loaded by hand | `setup/workspace_setup` provisions data, reference results and grants per workspace |
| Learners have a managed catalog, dropped at cleanup; learner-created catalogs are dropped too | Outputs go to `{managed_catalog}.mmf` (`labs/_includes/config`); no `CREATE CATALOG` in learner notebooks |
| Skill install had no automated path | `setup/user_setup` installs the skill bundle and templated instructions per user |
| No GPUs in labs; avoid external code | No GPU path in G2; `mmf_sa` wheel pinned and staged in a volume (`setup/VERSIONS.md`) |
| Shortcut slow steps ("cooking show") | Lab 4 reference results in `mmf.m5_reference`; every `catchup` copies in seconds |
| Autograde runs as admin with `username` / `table` | Checkpoints exit with JSON; `setup/autograde` writes the rubric table |
| `lab_end` must reap what learners create | `vocareum/scripts/python/mmf_lab_end.py` (jobs, runs, clusters, experiments) |

**Not tested on a workspace yet** — no CLI profile was available. Next steps:

1. Upload the `.cfg` and archives to the Vocareum course and run the test plan in `vocareum/README.md`.
2. Confirm the open items in `VOCAREUM.md §9` (admin cluster DBR / access mode, `lab_end.py` interface, `account users` grants, Genie Code enabled).
3. Write `prompts.md` per lab, and the missing Labs 02, 03 and 06.
4. Make the foundation vs CPU comparison fair in Lab 5 (backtest windows differ).

## 2026-10-18 — 3.1 Lecture tested on e2-demo-field-eng

Imported *3.1 Lecture — Backtesting and Forecast Stability* and `Includes/_backtest_explorer` (only these two — the lecture needs no `mmf.m5` data) into `/Users/<me>/mmf-workshop-test/` and ran the lecture as a one-off serverless job (environment `client: "4"`).

| Check | Result |
|-------|--------|
| Job run | SUCCESS (run `489454615407416`, task run `922024763919743`); `%run` and `displayHTML` cells ran without errors |
| `displayHTML` output | Identical to `BACKTEST_EXPLORER_HTML` (14,868 chars) — nothing stripped or escaped |
| Rendering | Exported run opened in Chrome: the widget renders inside Databricks' sandboxed output iframe |
| Defaults (56 / 28) | 2 windows; Steady seller Stable 95%, Intermittent Stable 100%, Promotions Fragile |
| Preset *MMF full (90 / 7)* | Sliders move to 90 / 7 and the charts re-render; Promotions becomes Moderate 88%, the others 100% — matches the lecture's answer block |
| Console | No errors and nothing from the widget (only Databricks viewer warnings from the `file://` origin) |

Dark mode checked by eye in the live notebook (2026-10-18): works well. Still to check: cell height. The other lessons were not tested on e2-demo (they need `workspace_setup`).

## 2026-10-18 — 4.2 Appendix (metric explorer) tested on e2-demo-field-eng

Metric semantics checked against `mmf_sa` at the pin (`abstract_model.calculate_metrics`, `MLForecastPipeline`): `metric` ∈ `smape` (default), `mape`, `mae`, `mse`, `rmse`, all sktime; only the chosen metric is stored, with the `forecast` / `actual` arrays. sktime replaces denominators below machine epsilon by epsilon, so MAPE on a zero-sales day ≈ 10¹⁵ and sMAPE of 0 vs 0 is 0.

One serverless job (3 tasks): a test harness wrote a synthetic MMF-shaped evaluation table (`users.lucas_bruand.mmf_test_eval`, 40 series × 4 models × 2 windows, scored with `sktime==0.40.1`); the appendix ran against it, and once more without data.

| Check | Result |
|-------|--------|
| Job run | SUCCESS (run `825005488496905`) — appendix with data `90540710307217`, without data `499456695586885` |
| Widget | Renders in the Databricks output iframe; markdown tables with escaped `\|` render; no console errors in the standalone test; ~10 ms per re-render |
| Presets (4 histories each) | Typical M5 item and Spare part: sMAPE, MAPE, MAE select Zero (bias −100%), RMSE the mean; Slow mover: MAPE selects Zero; Promotions: MAE → median (bias ≈ −20%), RMSE → mean; Fast mover: metrics agree but stability is low (close candidates) |
| Section D SQL re-scoring | Recomputed sMAPE matches sktime's stored value to 4.4·10⁻¹⁶; per-profile and wins-per-model tables produced |
| Section D without reference results | Prints a skip message; later cells do nothing |

Not yet run on the real `mmf.m5_reference` results (Vocareum workspace).

## 2026-10-18 — 3.4 Appendix (exogenous variables) tested on e2-demo-field-eng

`mmf_sa` at the pin: future regressors go in `dynamic_future_numerical` / `_categorical` with a separate `scoring_data` table (future dates, no target), unioned at scoring; backtests use each window's actual regressor values. StatsForecast uses them only in ARIMA-type models (`uses_exog`: ARIMA, AutoARIMA, AutoRegressive, MFLES); LightGBM uses them as features (the skill's validated path). Regressors must be numeric and non-NULL (the data-quality check drops series otherwise). M5's `daily_train_100` already carries `snap_*`, `event_*` and `sell_price`.

Test: `setup/00_data_load` into `users.lucas_bruand` (cache volume `mmf_test_cache`), then the appendix on serverless with `mmf_sa` installed from GitHub at the pin (the only change from the course notebook). Run `1071930810179420`: SUCCESS in 8 min, *Check your work* PASS.

| | No regressors | With `snap`, `is_event`, `relative_price` |
|-|---------------|---------------------------------------------|
| Backtest sMAPE (2 windows) | 1.185 | 1.173 |
| Held-out 28 days: sMAPE / MAE / RMSE / WAPE / bias | 1.236 / 1.387 / 2.881 / 0.578 / +4.5% | 1.246 / 1.347 / 2.780 / 0.562 / +3.9% |
| Series improved (by category) | — | FOODS 59%, HOBBIES 58%, HOUSEHOLD 63% |

Lifts in the training data: SNAP ×1.16 FOODS vs ×1.04–1.07 others; discount days ×1.43–1.65; event days ×0.92–0.99. 99 of 100 series pass MMF's data-quality check.
