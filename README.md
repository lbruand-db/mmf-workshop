# MMF Workshop — Many-Model Forecasting with Genie Code

Hands-on workshop on [Many-Model Forecasting (MMF)](https://github.com/databricks-industry-solutions/many-model-forecasting) using Databricks Genie Code and the MMF skill on the M5 dataset.

## Overview

Participants use **Genie Code** (Databricks' AI coding agent) with the **MMF skill** to forecast ~100–1,000 retail time series end-to-end: data preparation, profiling, model execution, evaluation, and deployment. The skill guides each step via natural language prompts with built-in checkpoints.

**Dataset:** [M5 Forecasting Competition](https://www.kaggle.com/c/m5-forecasting-accuracy) — Walmart daily sales, sampled to 100 or 1,000 series.

**Models:**
- **Local statistical:** SeasonalNaive, AutoETS, AutoTheta, CrostonOptimized, TSB
- **Global ML:** LightGBM (MLForecast)
- **Foundation:** Chronos-Bolt-Small (pre-computed reference results)

## Repository structure

```
├── README.md
├── SPECS/
│   ├── SPEC.md              # Workshop specification
│   ├── VOCAREUM.md           # Vocareum environment research
│   └── NOTES.md              # Working notes and test results
├── setup/                    # Admin-only — never shipped to learners
│   ├── workspace_setup.py    # Once per workspace: data, skill bundle staging, grants
│   ├── user_setup.py         # Once per learner: install MMF skill for Genie Code
│   ├── 00_data_load.py       # Load M5 data into Unity Catalog (called by workspace_setup)
│   ├── 01_precompute_foundation.py  # Pre-compute foundation model results (CPU)
│   └── VERSIONS.md           # Pinned upstream versions
└── labs/
    ├── _includes/
    │   └── config.py         # Shared widgets + read/write locations (%run by every lab)
    ├── 00-setup/
    │   ├── catchup.py        # Create user schema, verify data and skills
    │   └── checkpoint.py     # PASS/FAIL validation
    ├── 01-prep/
    │   ├── catchup.py        # Copy training data to user schema
    │   └── checkpoint.py
    ├── 04-execute/
    │   ├── catchup.py        # Run CPU models (5 local + LightGBM)
    │   ├── catchup_foundation.py  # Run foundation models (GPU)
    │   └── checkpoint.py
    └── 05-evaluate/
        ├── catchup.py        # Best-model selection + evaluation summary
        └── checkpoint.py
```

## Where outputs go

Every lab notebook runs `labs/_includes/config` first, which prints the shared data location and the learner's output location:

| Environment | Reads from | Writes to |
|-------------|-----------|-----------|
| Vocareum | `mmf.m5` | `{managed_catalog}.mmf` — the per-user catalog Vocareum creates (e.g. `vocuser12345_vocareum_com`) and drops at lab end |
| Instructor-led workshop | `mmf.m5` | `mmf.{user}` — schema derived from the email |

Override with the `user_catalog` / `user_schema` widgets (job parameters). Learner notebooks never create catalogs.

## Lab independence

Every lab can be entered cold. Each lab directory contains:
- **`catchup.py`** — Bootstrap notebook that produces all expected outputs. Run this to skip to any lab without completing prior ones.
- **`checkpoint.py`** — PASS/FAIL validation that verifies the lab's outputs exist and are correct.

## Setup (instructor / admin)

Both setup notebooks run as a workspace admin and are safe to re-run. On Vocareum they are the `workspace_setup` and `user_setup` entries of the course `.cfg`, called with `host` / `token` (and `username`). For an instructor-led workshop, run them by hand.

### 1. Workspace setup — `setup/workspace_setup.py`

Run once per workspace. It:

1. Creates `mmf.m5` and the `mmf.m5.assets` volume.
2. Stages, from the upstream repo pinned by the `mmf_ref` widget (see `setup/VERSIONS.md`), the MMF skill bundle and agent instructions in `/Volumes/mmf/m5/assets/skills/`, and an `mmf_sa` wheel plus requirements files in `/Volumes/mmf/m5/assets/wheels/`.
3. Runs `00_data_load` (raw M5 files cached in the volume) and `01_precompute_foundation`, skipping either if its tables already exist (`force_reload=true` to redo):

   | Table | Description |
   |-------|-------------|
   | `daily_train_100` | 100 sampled series (seed=7) |
   | `daily_train_1000` | 1,000 sampled series (seed=7) |
   | `m5_static_features` | Item/store metadata |
   | `reference_evaluation_output` | Chronos-Bolt-Small results on CPU (100 series × 2 backtest windows) — needed because Vocareum has no GPU. Lab 5 merges them with participant results |

4. Grants `learner_group` (default `account users`) read-only access to `mmf.m5`. For an instructor-led workshop set `allow_user_schemas=true`, so participants can create their `mmf.{user}` schema.

### 2. User setup — `setup/user_setup.py`

Run once per learner, with `username` set to their email (comma-separated for several). It installs the staged bundle into `/Users/{email}/.assistant/skills/`, and `assistant_instructions.md` — with its `### User Context` filled in — as `/Users/{email}/.assistant_instructions.md`.

### Packaging

`uv run mmf-workshop build` writes two archives to `dist/`: `mmf-workshop-labs.dbc` (learner content) and `mmf-workshop-setup.dbc` (admin setup). Learners never receive the setup notebooks.

## Running the labs

### As a participant (with Genie Code)

1. Open Genie Code in the Databricks workspace
2. Follow the MMF skill prompts for each lab
3. If stuck, run the lab's `catchup.py` to bootstrap

### As a test (serverless jobs)

```bash
# Lab 4 — CPU forecast (100 series, ~10 min)
databricks jobs submit --json '{
  "tasks": [{"task_key": "main",
    "notebook_task": {"notebook_path": "/path/to/labs/04-execute/catchup",
      "base_parameters": {"catalog": "mmf", "user_schema": "u_test",
        "source_schema": "m5", "n_series": "100"}},
    "environment_key": "env"}],
  "environments": [{"environment_key": "env",
    "spec": {"client": "4", "dependencies": []}}]}'

# Lab 5 — Evaluate (~2 min)
databricks jobs submit --json '{
  "tasks": [{"task_key": "main",
    "notebook_task": {"notebook_path": "/path/to/labs/05-evaluate/catchup",
      "base_parameters": {"catalog": "mmf", "user_schema": "u_test",
        "source_schema": "m5", "metric": "smape"}},
    "environment_key": "env"}],
  "environments": [{"environment_key": "env",
    "spec": {"client": "4", "dependencies": []}}]}'
```

## Known limitations

- **No GPU on Vocareum:** Both EC2 GPU quota and serverless GPU are unavailable. Foundation models are pre-computed on CPU and stored as reference data.
- **MMF foundation models require GPU:** `run_forecast` with `accelerator="cpu"` silently skips foundation models. The pre-compute notebook uses `chronos-forecasting` directly instead.
- **`mmf_sa` not on PyPI:** `workspace_setup` builds it from the pinned upstream commit into `/Volumes/mmf/m5/assets/wheels/`; labs install it with `%pip install -r /Volumes/mmf/m5/assets/wheels/requirements-cpu.txt`. Pins are listed in `setup/VERSIONS.md`.

## Test results (2026-10-15)

| Step | Status | Detail |
|------|--------|--------|
| Data load | PASS | 3 tables in `mmf.m5` |
| Lab 4 CPU (100 series) | PASS | 6 models, 891 eval rows each |
| Lab 5 evaluate | PASS | 99 best models selected |
| Foundation pre-compute | PASS | ChronosBoltSmall, 200 eval rows, avg SMAPE 1.54 |
