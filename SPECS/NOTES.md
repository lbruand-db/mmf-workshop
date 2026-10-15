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
| **No GPU quota** | **Good news** | `g4dn.xlarge` (T4) is allowlisted in Personal Compute policy. Foundation models can run. Job Compute policy has unrestricted node types |
| **Upstream MMF changes** | Not yet mitigated | Need to pin SHA in `setup/VERSIONS.md` |
| **Network/SSO issues** | N/A for Vocareum | Vocareum handles learner access |
| **Write collisions** | Mitigated (plan) | Per-user schemas. `mmf` catalog + `m5` shared schema created. Need per-user schemas at setup time |
| **Serverless** | **Confirmed** | Serverless is enabled on the workspace. SQL warehouses are serverless-capable (PRO type) |

### Next steps to complete risk mitigation

1. **Load M5 data** into `mmf.m5` (run `data_preparation_m5.py` on this workspace — needs a running cluster or serverless notebook)
2. **Test Genie Code** in the browser — open the workspace, start a Genie Code session, and verify the skill is visible
3. **Run a full Lab 1–5 dry run** as a participant to time everything
4. **Pin the MMF SHA** and record it
5. **Create a test learner schema** (`mmf.u_testuser`) and verify permissions
6. **Build the setup scripts** (`setup/00_admin_setup.py`, etc.)
