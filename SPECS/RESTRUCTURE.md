# Restructure — course layout modelled on a reference Databricks course

> Status: phases 0–2 done (2026-10-16); phases 3–6 are the backlog below. Not yet run on a workspace (no CLI profile available) — phase 6 covers that.

## Context

We reorganise the workshop to follow the **layout and conventions** of an official Databricks training course whose source repo we were given for reference (kept outside the repo in `.sources/`, git-ignored). That material is copyrighted: **nothing from it is copied** — no text, code, images, HTML exports, or branding. We only reuse its structure, naming, and the platform interfaces it relies on (e.g. the `dbacademy.ops.meta` table, the course manifest format).

## Decisions (2026-10-16)

| # | Topic | Decision |
|---|-------|----------|
| 1 | Data provisioning | **Keep `setup/workspace_setup`** (no Marketplace listing for M5 for now) |
| 2 | Grading | **No grading.** Checks stay in each lesson as learner feedback only; `setup/autograde` is removed |
| 3 | Agent-driven labs | Golden-path Genie Code prompts and gate answers go in **collapsible ANSWER blocks** in the lesson (replaces the planned `prompts.md`) |
| 4 | Branding | **Neutral.** No Databricks Academy logo, header or footer — this is not an Academy course |
| 5 | Timing | Phases 0–2 now (mechanical); phases 3–6 after the 2026-10-20 workshop |

## Conventions adopted

| Convention | In this repo |
|------------|--------------|
| `labs/Source/<locale>/notebooks/` per language | `en_us` only for now |
| `AGENDA.py` as landing notebook: description, prerequisites, modules → lessons table with `$./` links, requirements | `notebooks/AGENDA.py` |
| Module folders `M0x - <Name>/` with numbered lessons `x.y Lecture / Demo / Lab / Appendix - <Title>` | See layout below |
| `Includes/_common.py` resolving per-user locations, reading `dbacademy.ops.meta` when the platform provides it | Our own implementation (was `labs/_includes/config.py`) |
| `Includes/Classroom-Setup-<x.y>.py` run at the top of each lesson, putting the lesson's **prerequisites** in place | Replaces the per-lab `catchup.py`: every lesson can be entered cold |
| Serverless environment header (`# /// script` … `environment_version`) on each notebook | Added; version `4`, matching what was tested |
| `Version Info.py`, `Includes/Print-Dataset-Copyrights.py` | Ours; version and build date filled in by `mmf-workshop build` |
| `voc/docs/README.md` next to the notebooks | Moved from `vocareum/docs/README.md` |

Lesson notebook skeleton: title and overview → *Before you start: compute* → *Classroom setup* (`%run ../Includes/Classroom-Setup-x.y`) → learning objectives → lettered sections / tasks → *Check your work* (`Includes/_checks`) → summary.

## Target layout

```
labs/Source/en_us/
├── notebooks/                                  # → course zip, entry: AGENDA
│   ├── AGENDA.py
│   ├── Version Info.py
│   ├── Includes/
│   │   ├── _common.py  _checks.py
│   │   ├── Classroom-Setup-1.2.py  -2.2  -3.2  -3.3  -4.1
│   │   └── Print-Dataset-Copyrights.py
│   ├── M01 - Many-Model Forecasting Foundations/
│   │   ├── 1.1 Lecture - Why Many-Model Forecasting          (phase 4)
│   │   └── 1.2 Demo - Genie Code and the MMF Skill           (was Lab 0)
│   ├── M02 - Preparing Many Series/
│   │   ├── 2.1 Lecture - Data Quality for Time Series        (phase 4)
│   │   ├── 2.2 Demo - Prep and Clean with Genie Code         (was Lab 1)
│   │   └── 2.3 Lab - Profile and Classify Series             (phase 4, Skill 2)
│   ├── M03 - Running Forecasts at Scale/
│   │   ├── 3.1 Lecture - Backtesting and Forecast Stability  (done 2026-10-18: interactive JS explorer)
│   │   ├── 3.2 Demo - MMF with mmf_sa                        (was run_cpu.py; also the reference solution)
│   │   └── 3.3 Lab - Provision and Execute with Genie Code   (was Lab 4; Skill 3 in phase 4)
│   └── M04 - Evaluating and Selecting Models/
│       ├── 4.1 Lab - Best Model per Series                   (was Lab 5)
│       └── 4.2 Appendix - Forecast Accuracy Metrics          (phase 4)
├── instructor/
│   └── Foundation Models on GPU.py             # was run_foundation.py; not in the learner zip
└── voc/docs/README.md
```

Lesson numbers are final, so links don't change when the missing lectures are added.

## Backlog

### Phase 3 — Rewrite the existing lessons
- Demo/Lab form: overview, objectives, tasks, summary.
- Labs: `<FILL_IN>` cells with collapsible **ANSWER** blocks (HTML `<details>` in a markdown cell, our own styling). For Genie Code tasks, the ANSWER block holds the golden-path prompt and the expected answer at each STOP gate, with a short "why" for self-paced learners.
- The "short on time" cells (copy reference results) move into ANSWER blocks.
- Check whether the environment header can declare `mmf_sa` (replacing the `%pip install -r` cell), and whether to move to environment version 5 (the reference course uses 5; we tested on 4).

### Phase 4 — New content
- Lectures 1.1, 2.1, 3.1 (markdown-only notebooks, our own diagrams in `Includes/images/`).
- Lab 2.3 Profile and Classify Series (Skill 2), Skill 3 provisioning in Lab 3.3, Appendix 4.2 metrics.
- Make the Lab 4.1 foundation vs CPU comparison fair (same backtest windows, common series).
- Electives later: M05 Hierarchical Reconciliation, M06 MLOps (G3).

### Phase 5 — Packaging
- `manifest.yaml` in the course-vending format, replacing `vocareum/courseware/mmf-workshop.cfg`. First confirm that the format supports our `workspace_setup` / `user_setup` hooks (decision 1).
- Root `README.md` restructured: description, data assets, Vocareum lab notes (compute, environment, users per workspace, lab time), change log.
- `voc/docs/README.md` linking to pre-run HTML exports of our own notebooks (`voc/docs/HTML_Files/M0x_…/`), generated by `mmf-workshop build`.
- Update `vocareum/README.md` and SPECS.

### Phase 6 — Verify
- Import the zip, run AGENDA → every lesson cold and in order, and check `dbacademy.ops.meta` resolution on a Vocareum workspace (its keys and values are not verified yet).
- Run `workspace_setup`, then the HTML export.
