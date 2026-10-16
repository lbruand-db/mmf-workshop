# Vocareum Environment — Running MMF

> Research note for the MMF workshop spec (see `SPEC.md §8`).
> Last updated: 2026-10-16.
>
> **Sources:** L&E Confluence — *Field-Driven Enablement Labs in Vocareum* (go/field-driven-enablement-labs), *Vocareum Lab Development Guidelines* (go/vocareum-lab-guidelines), *Lab Development on Vocareum* (go/vocareum-lab-development). Help: #field-driven-labs-vocareum.
>
> **Implementation:** `vocareum/README.md` has the concrete course settings, uploads and test plan.

---

## 1. How Databricks labs work on Vocareum

Databricks Field Engineering runs Vocareum labs as **Cloud Labs — Databricks**: Vocareum provisions real Databricks workspaces and redirects learners into them. This is the only option for MMF, which needs Genie Code, Unity Catalog, serverless compute, MLflow and Jobs.

| Fact | Consequence for MMF |
|------|---------------------|
| **AWS only** (Azure expected by end of FY26) | Use AWS instance types; no Azure/GCP features |
| **Shared workspaces**: each part sets a max number of users per workspace; Vocareum opens another workspace when it's full | No per-learner workspaces. Set the limit as high as product limits allow |
| **One metastore per workspace** (no longer a global metastore) | Shared data must be loaded **per workspace** by `workspace_setup`; it can't be loaded once by hand |
| **Learners are workspace users, not admins**; nobody can reach the AWS account or the E2 account | All admin work (catalogs, grants, data load, skill install) runs in admin hooks |
| **Managed catalog per user**, named after the Vocareum username (`vocuser12345@vocareum.com` → `vocuser12345_vocareum_com`). Learners have all privileges in it but can't drop it; it is dropped at user cleanup | Learner outputs go to `{managed_catalog}.mmf` — isolated, with cleanup for free |
| Learners may create catalogs, but **any catalog a learner creates is dropped at their cleanup** | Learner notebooks must never `CREATE CATALOG` — a learner-created `mmf` would take the shared data with it |
| Learners have `SELECT ON ANY FILE` | — |
| Orgs map to cost centres; use the **GenAI** org for serverless-enabled workspaces | Clone the course template in the GenAI org |

## 2. L&E guidelines that apply to MMF

**Do:**
- Keep cost down (Vocareum, AWS and DBU costs): give learners the **minimum** compute and data size → 100 series by default, serverless.
- Use shared resources through Unity Catalog → read-only `mmf.m5` and `mmf.m5_reference`.
- Pre-create what isn't a learning objective → data, reference results and the skill install are all automated.
- Include a `README.md` with objectives, instructions and resources → `labs/Source/en_us/voc/docs/README.md`.
- Shortcut slow tasks "like a cooking show" → each lesson's Classroom setup and *Short on time?* cells copy pre-computed results in seconds.
- Identify quotas and limits early (Jobs, serverless, Genie Code concurrency per workspace).
- Set the session length thoughtfully, and the budget to **at most 3×** the session length.
- Automate setup **and** termination: `lab_end` must reap what the lab creates.

**Don't:**
- **Use GPUs** — expensive, and taken from customers. → No GPU path on Vocareum at all; foundation models come from pre-computed reference results.
- Use provisioned throughput model serving.
- Use third-party resources (external APIs, code, libraries) where avoidable. → `mmf_sa` is installed from a wheel pinned and staged in a volume, not from GitHub.
- Use private-preview features that need workspace-level enablement without an API. → Genie Code, Databricks Apps (Results Explorer), serverless GPU. Request enablement at go/lpt-general-request.

## 3. Course structure and files

Course → Assignment → Part. L&E usually makes one Assignment with one Part per lab; each part has its own workspace configuration. Clone an existing template (**Clone by Copy**) rather than starting from scratch.

**Part settings that matter:** Lab Type *Databricks*; users per workspace; Session Length (240 min standard); Time Budget; **End Lab Behavior = terminate** (with *stop*, `lab_end` doesn't run); Timer and Readme button on; LTI on for Docebo, off for direct enrolment; Course Feedback on.

**Files** (Configure Workspace → Files). **Never click "save image"**: `/voc` is already persisted on NFS, and images use up the team's limited container slots.

```
/voc/private/courseware/   # course .cfg + notebook archives (+ optional dbfs/, patches/)
/voc/docs/README.md        # learner instructions, shown in the side pane
/scripts/                  # .sh wrappers → /scripts/python/*.py
    workspace_init.py      #   on workspace creation (can be re-run)
    user_setup.py          #   on user creation
    lab_setup.py           #   on lab start
    lab_end.py             #   on End Lab / session expiry — reap resources here
```

### `.cfg` keys

A JSON file in the course folder ending in `.cfg`. A *DBC object* is `{src, entry?, folder?, patch?}`; `src` is a path to an archive in the course folder (the platform's own example uses a `.zip`).

| Key | Runs as | Receives | MMF use |
|-----|---------|----------|---------|
| `content` | — | — | `mmf-workshop-labs.zip`, opens `AGENDA` |
| `workspace_setup` | admin (workspace + metastore) | `host`, `token` | `setup/workspace_setup` |
| `user_setup` | admin | `host`, `token`, `username` | `setup/user_setup` |
| `autograde` | admin | `host`, `token`, `username`, `table` | Not used — the course is not graded |
| `admin_cluster_config` | — | — | Cluster that runs the hooks above (DBR, node type, Spark confs, libraries) |
| `cluster_config` / `warehouse_config` | — | — | Managed per-user compute. **Not used**: learners run on serverless |
| `secrets`, `enable_dbfs`, `entry` | — | — | Not used |

A `dbfs/` subfolder of the course folder is copied into DBFS; `patches/` holds hotfix replacements for notebooks in an archive.

## 4. Lifecycle mapped to this repo

| Vocareum event | What runs | Effect |
|----------------|-----------|--------|
| Workspace created | `setup/workspace_setup` | `mmf.m5` data, foundation reference results, Lab 4 reference results in `mmf.m5_reference`, skill bundle and `mmf_sa` wheel in `/Volumes/mmf/m5/assets`, read-only grants to learners |
| Learner added | `setup/user_setup` | MMF skill and templated `.assistant_instructions.md` in `/Users/{username}/` |
| Lab start | `content` | Course notebooks imported into the learner's folder as `mmf-workshop/` |
| Lab end | template `lab_end.py` → `vocareum/scripts/python/mmf_lab_end.py` | Cancels runs; deletes the learner's jobs (Skill 4), clusters (Skill 3) and MLflow experiments. Vocareum drops the managed catalog itself |

## 5. Grading

The `autograde` notebook must create the table named by its `table` parameter with this schema, one row per rubric:

| Column | Type | Meaning |
|--------|------|---------|
| `rubric` | `VARCHAR(255)` | Rubric name, as defined in the Vocareum part configuration |
| `score` | `INT` | 0 to that rubric's maximum score |
| `feedback` | `VARCHAR(255)` | Required when the score is below the maximum |

**Not used:** the MMF course is not graded (decided 2026-10-16); each lesson's *Check your work* is learner feedback only. Kept here for reference. Grades would flow back to the LMS through LTI when it is enabled.

## 6. Compute

| Model class | Examples | Compute | Vocareum path |
|-------------|----------|---------|---------------|
| Local statistical | SeasonalNaive, AutoETS, AutoTheta, Croston, TSB | CPU | Serverless — learners run it |
| Global ML | LightGBM (MLForecast) | CPU | Serverless — learners run it |
| Global DL | NeuralForecast (NHITS, TFT, PatchTST) | GPU | Not offered |
| Foundation | Chronos, TimesFM, Moirai | GPU | **Reference results only**: pre-computed on CPU by `workspace_setup` (`01_precompute_foundation`, Chronos-Bolt-Small) and merged in Lab 5 |

Measured on the Vocareum test workspace (2026-10-15): there is no GPU EC2 quota (`AWS_RESOURCE_QUOTA_EXCEEDED` on `g4dn.xlarge`), and serverless GPU is not enabled. This matches the guideline. Don't ask for GPU quota for this course.

The MMF skills can still provision clusters (Skill 3 offers 16/32 vCPU CPU and GPU options). The learner instructions steer learners to the smallest CPU option, `lab_end` deletes whatever they create, and a cluster policy restricting learner clusters would make this airtight.

## 7. Genie Code

- The workspace must be Premium or Enterprise; Genie Code is pay-as-you-go with a free monthly allowance per user.
- The skill must sit at exact paths: the bundle's contents flat in `/Users/{user}/.assistant/skills/` and the instructions at `/Users/{user}/.assistant_instructions.md`. The leading dots matter. `setup/user_setup` installs both and fills in the `### User Context` block.
- **Still to confirm:** that Genie Code is enabled on Vocareum-provisioned workspaces in the GenAI org, and its concurrency limits for a full workspace of learners.

## 8. Cost per learner (rough)

| Component | Estimate |
|-----------|----------|
| Serverless notebooks and jobs, 100 series (Labs 0–5) | ~$2–4 |
| Genie Code | Free allowance is likely enough for one course |
| Shared setup per workspace (data load, reference runs on the admin cluster) | One-off, split across all learners in the workspace |
| **Total** | **~$2–4**, plus Vocareum and AWS platform costs |

What learners leave running dominates the cost. That's why End Lab Behavior must be *terminate* and `lab_end` must reap jobs and clusters.

## 9. Open questions

| # | Question | Status |
|---|----------|--------|
| 1 | Cloud/region | **AWS** (only option) |
| 2 | GPU / serverless GPU | **Not used** — against guidelines, and unavailable anyway |
| 3 | Per-learner or shared workspace | **Shared**, with a users-per-workspace limit and per-user managed catalogs |
| 4 | Packaging format | **`.cfg` + archives** in `/voc/private/courseware`, README in `/voc/docs` — see `vocareum/README.md` |
| 5 | Can setup call the Databricks APIs? | **Yes** — `workspace_setup` / `user_setup` get `host` and `token` |
| 6 | Genie Code enabled on provisioned workspaces? | **Open** — check in Student View; otherwise go/lpt-general-request |
| 7 | Admin cluster DBR and Unity Catalog access mode for `/Volumes` | **Open** — check on first deployment |
| 8 | How the template's `lab_end.py` receives `host` / `token` / `username` | **Open** — check in the cloned template |
| 9 | Does `account users` cover Vocareum learners (for grants)? | **Open** |
