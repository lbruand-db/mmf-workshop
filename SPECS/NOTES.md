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

**To fix properly:** ask Vocareum to either (a) increase the AWS GPU instance quota for g4dn.xlarge, or (b) enable serverless GPU (AI Runtime) on the workspace.

### Next steps to complete risk mitigation

1. ~~**Load M5 data** into `mmf.m5`~~ — DONE: `daily_train_100`, `daily_train_1000`, `m5_static_features`
2. ~~**Test Lab 4 (CPU)**~~ — DONE: 6 models × 100 series, 891 eval rows each
3. ~~**Test Lab 5**~~ — DONE: best-model selection works, 99 series ranked
4. **Pre-compute foundation results** — IN PROGRESS: Chronos-2 on CPU (run 1009123303309902)
5. **Test Genie Code** in the browser — verify the skill is visible
6. **Run a full Lab 1–5 dry run** as a participant to time everything
7. **Pin the MMF SHA** and record it
8. **Create a test learner schema** (`mmf.u_testuser`) and verify permissions
9. **Build the Vocareum setup scripts** (`voc/scripts/workspace_init.sh`, etc.)
