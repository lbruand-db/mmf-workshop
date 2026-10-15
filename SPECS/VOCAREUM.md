# Vocareum Environment Research — Running MMF

> Research note for the MMF workshop spec (see `SPEC.md §8`).
> Last updated: 2026-10-15.

---

## 1. Vocareum platform overview

Vocareum provisions per-learner lab environments in the browser. Three delivery models are relevant:

| Model | What the learner gets | GPU? | Best for |
|-------|----------------------|------|----------|
| **Vocareum Notebook** (Container architecture) | Managed Jupyter container with CPU or GPU toggle | Yes — admin-enabled, time-budgeted per student | Python/ML notebooks, no cloud console needed |
| **Cloud Labs — Databricks** | A real Databricks workspace (shared or per-learner), accessed via redirect | Yes — whatever the underlying workspace supports (classic clusters or serverless) | Our case: Genie Code + MMF skills + Unity Catalog |
| **VM Labs** (customer-managed AWS) | Full EC2 instances; allowlisted instance types include GPU families (G4dn/T4, G5/A10G, G6/L4, G6e/L40S, P5/H100) | Yes — any allowlisted EC2 type | Heavy GPU training, multi-VM topologies |

**For the MMF course we need Cloud Labs — Databricks**, because we require Genie Code, Unity Catalog, serverless compute, MLflow, and Databricks Jobs. A Vocareum Notebook alone cannot provide these.

## 2. How Vocareum provisions Databricks

### 2.1 Setup flow
1. **Org-level**: admin connects Vocareum to a Databricks account and supporting cloud infra (AWS or Azure), via the "Setting Up Databricks Resources" guide.
2. **Course-level**: admin creates a Databricks assignment. Configures the max users per workspace (learners can share a workspace with isolated schemas, or get one workspace each).
3. **Per-learner hooks** — shell scripts under `/voc/scripts/`:

| Script | Runs when | Use for MMF |
|--------|-----------|-------------|
| `workspace_init.sh` | After workspace creation | One-time: create catalog, shared M5 schema, deploy Results Explorer app |
| `lab_setup.sh` | Lab start | Per-lab: create learner schema, install MMF skills, run `catchup.py` for that lab |
| `user_setup.sh` | Lab start (after `lab_setup.sh`) | Per-user: template `.assistant_instructions.md` with user email |
| `lab_end.sh` | Lab end | Cleanup: terminate clusters, optionally drop learner schema |

4. **End-of-session options**: "Stop resources" (preserves state for next session) or "Terminate resources" (resets to original state). For a self-paced course, "Stop" is better — learners resume where they left off.

### 2.2 File layout (`/voc/`)
Vocareum expects this structure:
```
/voc/
├── startercode/    # Notebooks imported into the learner's workspace
├── data/           # Read-only datasets (small); large data pre-staged in the workspace
├── docs/           # README shown to learners in the Vocareum UI panel
└── scripts/        # workspace_init.sh, lab_setup.sh, user_setup.sh, lab_end.sh
```

### 2.3 Grading
- A `grade.sh` script writes scores to a CSV that Vocareum records.
- Maps directly to our `checkpoint.py`: the grader runs it and emits PASS (100) or FAIL (0).
- Grades pass back to the LMS (Canvas, Moodle, etc.) via LTI.

## 3. Compute options for MMF on Vocareum

### 3.1 Serverless (CPU) — the default path

Databricks serverless notebooks and serverless jobs are available if enabled on the provisioned workspace. This is the **recommended default** for the MMF course:
- No cluster startup wait (critical for a self-paced lab where learners shouldn't wait 5+ min).
- No per-learner cluster management or quota planning.
- Runs all MMF local and global ML model classes (StatsForecast, MLForecast/LightGBM).
- Cost is pay-per-use; no idle compute waste.

**Limitation:** serverless CPU cannot run foundation models (Chronos-2, TimesFM) or global DL models (NeuralForecast) — these require GPU.

### 3.2 Serverless GPU (AI Runtime) — foundation/DL models

As of 2026, Databricks AI Runtime provides serverless GPU environments (public preview). If available in the Vocareum-provisioned workspace's region:
- Foundation and DL models can run on serverless GPU notebooks/jobs without managing clusters.
- No startup delay beyond initial provisioning.
- Genie Code can guide GPU training/fine-tuning in AI Runtime notebooks.

**Open question:** AI Runtime serverless GPU availability is region-dependent and still in preview. Need to confirm:
1. Which cloud/region Vocareum provisions for Databricks Cloud Labs.
2. Whether AI Runtime is enabled there.
3. Cost per learner per lab session (GPU time budget).

### 3.3 Classic GPU clusters — fallback for foundation/DL

If serverless GPU is not available, provision classic GPU clusters via cluster policies:

| Cloud | Recommended GPU instance | GPU | VRAM | Use case |
|-------|--------------------------|-----|------|----------|
| **AWS** | `g5.xlarge` | 1× A10G | 24 GB | Foundation models (Chronos-2, TimesFM) — single GPU is sufficient |
| **AWS** | `g4dn.xlarge` | 1× T4 | 16 GB | Budget option; slower but works for Chronos-2 |
| **AWS** | `g6.xlarge` | 1× L4 | 24 GB | Newer, good availability |
| **Azure** | `Standard_NC4as_T4_v3` | 1× T4 | 16 GB | Budget option |
| **Azure** | `Standard_NC8as_T4_v3` | 1× T4 | 16 GB | More CPU/RAM headroom |

**Cluster policy** (enforced via `workspace_init.sh`):
- Restrict to the GPU instance types above (no learner-chosen expensive instances).
- Force DBR ML GPU runtime (e.g. `16.x-gpu-ml-scala2.12` or later).
- Auto-termination: 15–20 min idle.
- Single node (driver-only) or max 1 worker — MMF foundation models don't need multi-node.
- Single User data security mode (required for Unity Catalog).

**Cost concern:** a classic GPU cluster running for the duration of a lab (1–2 h) per learner is expensive at scale. At ~$1.00–$1.50/h (instance + DBU) × 30 learners × 2 h = $60–$90 just for GPU labs. Mitigations:
- Use GPU only for the foundation model lab (Lab 4), not all labs.
- Auto-terminate aggressively (15 min).
- Default to 100-series dataset on GPU labs to keep job runtime < 10 min.
- Or: skip learner GPU entirely and use pre-computed reference results (§3.5).

### 3.4 MMF model classes vs compute matrix

| Model class | Examples | Compute required | Vocareum path |
|-------------|----------|------------------|---------------|
| Local statistical | SeasonalNaive, AutoETS, AutoTheta, Croston, TSB | CPU | Serverless (default) |
| Global ML | LightGBM via MLForecast | CPU | Serverless (default) |
| Global DL | NeuralForecast (NHITS, TFT, PatchTST) | GPU | Serverless GPU or classic GPU cluster |
| Foundation | Chronos-2, TimesFM 2.5, Moirai | GPU | Serverless GPU or classic GPU cluster |

### 3.5 No-GPU fallback: reference results + demo

If GPU is not available or too expensive for a self-paced course:
- Foundation/DL results are **pre-computed** and staged in `{catalog}.m5_reference`.
- Lab 4 runs only local + global ML models (CPU, serverless, ~5–10 min on 100 series).
- Foundation model results are loaded from reference tables and explored in Lab 5 alongside the learner's own CPU results.
- An optional video or instructor demo shows the foundation model run.

This is the **safest default** for the Vocareum course until GPU availability and cost are confirmed.

## 4. Genie Code on Vocareum

Genie Code is the primary interface for the MMF workshop. Requirements:
- The Databricks workspace must be **Premium or Enterprise** tier (Genie Code is not available on Standard; note Azure Standard tier retires 2026-10-01).
- Genie Code billing is pay-as-you-go (since July 2026) with a free monthly per-user allowance.
- The MMF skill bundle must be installed per-user at the exact paths (`/Users/{user}/.assistant/skills/` and `/Users/{user}/.assistant_instructions.md`). The `user_setup.sh` hook handles this.

**Open question:** confirm that Genie Code is available on Vocareum-provisioned Databricks workspaces. It should be (it's a workspace feature, not a Vocareum feature), but the workspace tier and entitlements must be right.

## 5. Recommended Vocareum architecture for the MMF course

### Option A — shared workspace, per-learner schema (recommended)
- **1 workspace** per cohort (up to ~50 learners).
- Each learner gets their own schema (`{catalog}.u_{shortname}`).
- Shared read-only data in `{catalog}.m5`.
- Shared cluster policies, Results Explorer app, and reference results.
- **Pros:** simpler provisioning, lower fixed cost, shared resources.
- **Cons:** noisy-neighbor risk on concurrent serverless jobs; workspace-level settings shared.

### Option B — per-learner workspace
- Each learner gets their own workspace.
- Full isolation; no contention.
- **Pros:** no resource contention, cleaner.
- **Cons:** much higher provisioning cost and time; M5 data must be replicated per workspace (or shared via a central metastore); more complex setup scripts.

**Recommendation:** Option A for cost and simplicity. The per-user schema + `use_case` prefix provides sufficient isolation for the MMF pipeline. Serverless compute handles concurrency well.

## 6. Cost estimation per learner

| Component | Option A (serverless CPU only) | Option A (serverless CPU + classic GPU) |
|-----------|-------------------------------|----------------------------------------|
| Serverless compute (Labs 0–3, 5) | ~$2–4 (1–2 h of notebook + job DBUs on 100 series) | ~$2–4 |
| GPU cluster (Lab 4 foundation models, 15–30 min) | N/A — use reference results | ~$0.75–$1.50 |
| Genie Code | Free allowance likely sufficient for 1 course | Same |
| SQL warehouse (Results Explorer app) | Shared; ~$0.50–$1 per learner | Same |
| **Total per learner** | **~$3–5** | **~$4–7** |

These are rough estimates. Actual cost depends on cloud/region, instance pricing, and how long learners leave things running. The `lab_end.sh` hook terminating all resources is critical for cost control.

## 7. Summary of open questions for Vocareum

| # | Question | Blocking? |
|---|----------|-----------|
| 1 | Which cloud and region does Vocareum provision Databricks workspaces in? | Yes — determines GPU instance availability |
| 2 | Is AI Runtime (serverless GPU) available in that region? | Yes — determines whether foundation models need classic clusters |
| 3 | Is Genie Code available on the provisioned workspace tier? | Yes — core dependency |
| 4 | Shared workspace (Option A) or per-learner workspace (Option B)? | Yes — drives setup script design |
| 5 | Per-learner compute budget / time cap? | No — but needed for cost planning |
| 6 | Exact Course Vendor packaging format (manifest, ZIP structure)? | No — needed for G2 delivery, not for G1 |
| 7 | Can `workspace_init.sh` run Databricks CLI commands (e.g. `databricks workspace import-dir`)? | Yes — needed for skill installation |

## 8. Recommendation

**For the initial Vocareum course, default to serverless CPU only (no GPU).** Use the 100-series dataset and the local + global ML model set. Foundation model results come from pre-computed reference tables. This eliminates GPU quota, cost, and availability risks entirely.

Add GPU as an **elective upgrade** once we confirm:
- The cloud/region and GPU instance availability.
- AI Runtime serverless GPU or a viable classic GPU cluster policy.
- An acceptable per-learner GPU cost budget.

This matches the lab independence principle: the foundation model lab works with or without GPU, because `catchup.py` can load reference results either way.
