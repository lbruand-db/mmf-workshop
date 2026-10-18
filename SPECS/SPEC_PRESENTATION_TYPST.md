# SPEC — Presentation: Typst Slide Deck

| | |
|---|---|
| **TODO item** | [ ] Let's add a pdf typst presentation |
| **Status** | Draft for review — 2026-10-18 (revised: built on the `typst-dbrx-template`) |
| **Proposed lesson / artefact** | PDF slide deck for the 2-hour customer workshop (G1, 2026-10-20), also offered as a reference PDF for the Vocareum course (G2). Not a lesson. |
| **Type / time** | ~20 slides; ~20 min of speaking outside the lessons |
| **Template** | [lbruand-db/typst-dbrx-template](https://github.com/lbruand-db/typst-dbrx-template) (private), pinned at `3def5debb70a486e46324b67f6466b1719f1b591` (2026-06-29) |
| **Compute** | Local `typst compile` (Typst 0.14.2) or CI |

## 1. Goal and outcomes

A short, Databricks-branded slide deck that frames the hands-on workshop: why many-model forecasting, what MMF and the MMF skill are, the agenda, one transition slide per lesson, and a wrap-up. Hands-on time dominates: the lessons take 100 of the 120 minutes, so the slides get about 20 minutes — ~10 for the introduction, short transitions inside the lesson slots, 5–10 for the wrap-up (agenda in `labs/Source/en_us/notebooks/AGENDA.py`).

Outcomes:
1. The instructor can run the session from one PDF that matches the course's lesson names and timings.
2. The deck is built from source in this repo with one command, and records the git commit it was built from.
3. G2 learners can download the same deck (minus the transition slides, if preferred) as a reference.

## 2. Background — the template

The deck uses **`typst-dbrx-template`**, a Typst reproduction of the 2025 Databricks corporate slide deck. What it provides (read from its `README.md`, `CLAUDE.md`, `dbrx.typ` and `compile.sh` at the pinned commit):

| | |
|---|---|
| Library | `dbrx.typ` — `#import "dbrx.typ": *` then `#show: dbrx-presentation.with(title:, author:, subject:, footer:, page-numbers:)` |
| Slide functions | `title-slide` (variants dark / coral / light), `section-slide`, `content-slide` (optional `subtitle:`, `dark: true`), `two-column-slide`, `three-column-slide`, `card-slide` (2–4 cards), `panel-slide`, `box-slide`, `quote-slide`, `headline-slide`, `image-slide`, `pdf-slide`, `summary-slide`, `takeaway-slide`, `board-slide`, `resource-slide`, `freeform-slide`, blanks |
| Utilities | `dbrx-table`, `dbrx-qr-code(url)` (QR with the Databricks mark), `dbrx-mermaid(definition)` (themed Mermaid diagrams), `dbrx-icon-row`, `dbrx-ribbon` |
| Brand | Barlow font (5 weights, bundled in `fonts/`), Databricks colours (`dbrx-navy`, coral/red, teal, …), logos in `assets/` |
| Footer | Every slide: red mark + footer text (default `©2026 Databricks, Inc. — All rights reserved`) + page number |
| Build | `compile.sh <file>.typ` → `typst compile --font-path fonts/ --input commit_id=$(git rev-parse HEAD) …`; the commit id goes into the PDF keywords |
| Dependencies | Typst 0.14.2; Typst Universe packages imported by `dbrx.typ`: `@preview/cades:0.3.1` (QR), `@preview/muchpdf:0.1.2` (PDF pages), `@preview/mmdr:0.1.0` (Mermaid) — downloaded on first compile, then cached |
| CI example | `.github/workflows/compile.yml` — `typst-community/setup-typst@v4`, then `./compile.sh`, upload the PDF as an artifact |

Consequences for this spec:
- **Branding is settled:** the deck is Databricks-branded (logo, colours, Barlow). This is consistent with the course rule — *neutral* means "not Databricks Academy", not "no Databricks". No Academy marks anywhere.
- **No speaker notes in the template** (no Touying / Polylux, no `pdfpc` notes). Notes need another home — see Decision 3.
- **Diagrams** can be drawn with `dbrx-mermaid` instead of exported images, so they stay editable in source and on-brand.
- Both this repo and the template are **private**, so either can reference the other; anyone building the deck needs access to the template (or a vendored copy).

## 3. Proposed content (slide-by-slide, with template functions)

### Part 1 — Introduction (~10 min, slides 1–9)

| # | Slide | Function | Content |
|---|-------|----------|---------|
| 1 | Title | `title-slide(variant: "dark")` | *Many-Model Forecasting with Genie Code* — subtitle *Hands-on workshop on Databricks*; presenter, date |
| 2 | Agenda | `content-slide` + `dbrx-table` | 0:00 intro · 1.2 Demo (15 min) · 2.2 Demo (25 min) · M03: 3.3 Lab, with the 3.2 instructor demo while jobs run (30 min) · 4.1 Lab (30 min) · wrap-up. Optional lessons listed as "after the workshop": 3.1, 3.4, 4.2 |
| 3 | Why many models? | `headline-slide` | "Thousands of series, no single model wins everywhere" — let each series pick its model, judged by backtests |
| 4 | Three model classes | `card-slide` (3 cards) | Local (StatsForecast: Seasonal Naive, AutoETS, Croston, TSB — refitted per series) · Global (LightGBM — one model across series) · Foundation (Chronos-Bolt — pretrained, zero-shot; precomputed here, no GPU) |
| 5 | How MMF runs | `content-slide` + `dbrx-mermaid` | Train table → `run_forecast` → backtest windows (`prediction_length`, `backtest_length`, `stride`) → evaluation and scoring tables, MLflow → best model per series |
| 6 | The dataset | `two-column-slide` | M5 (Walmart daily unit sales, item × store); 100 sampled series; weekly pattern, events, SNAP days, many zero-sales days. Attribution as in *Version Info* |
| 7 | Genie Code + the MMF skill | `content-slide` | The six MMF skills (1 prep and clean, 2 profile, 3 provision, 4 execute, 5 evaluate, 6 reconcile) and their STOP gates; which ones the workshop uses (1 in 2.2, 3–4 in 3.3, 5's logic in 4.1) |
| 8 | What you'll do | `takeaway-slide` | The four lesson outcomes, one line each |
| 9 | How the lessons work | `content-slide` | Classroom setup cell · *Short on time?* cells · *Check your work* · jobs keep running in the background — don't wait |

### Part 2 — Transitions (inside the lesson slots, slides 10–13)

One slide per core lesson, `section-slide(variant: "coral")` or `content-slide`: lesson name and time, the one question to answer, a visual.

| # | Lesson | Question / visual |
|---|--------|-------------------|
| 10 | 1.2 Demo — Genie Code and the MMF Skill (15 min) | "Does Genie Code list the MMF skill?" · `assets/screenshot.png` |
| 11 | 2.2 Demo — Prep and Clean with Genie Code (25 min) | "How many series are mostly zeros?" — remember it for M04 |
| 12 | M03 — 3.3 Lab with the 3.2 demo (30 min) | "Did your jobs start?" Jobs take 10–20 min: don't wait, use *Short on time?*, move to 4.1. Optional later: 3.1 (backtest explorer), 3.4 (exogenous variables) |
| 13 | 4.1 Lab — Best Model per Series (30 min) | "Which model class wins where — and why?" Optional later: 4.2 (metric explorer) |

### Part 3 — Wrap-up (5–10 min, slides 14–19)

| # | Slide | Function | Content |
|---|-------|----------|---------|
| 14 | Key takeaways | `summary-slide` | No single model wins everywhere · judge models on several backtest windows · pick the metric for your series (zeros!) · Genie Code + MMF skill take you from table to forecasts |
| 15 | Beyond today | `board-slide` | Columns from `SPEC_INDEX.md`: theory (1.1, 2.1, 3.5, 4.3, 4.4), data (2.3–2.5), production (M05), foundation models (M06) — marked "planned" until built |
| 16 | From 100 series to yours | `content-slide` | What changes at scale: more series → more parallel tasks for local models; backtest settings and model set drive cost (see SPEC_SCALING). No numbers until measured |
| 17 | Resources | `resource-slide` + `dbrx-qr-code` | MMF repository, the course, FPP3, Databricks docs |
| 18 | Thank you / Q&A | `headline-slide(variant: "dark")` | |
| 19 | Dataset attribution | `content-slide` | M5 attribution, matching `Includes/Print-Dataset-Copyrights` |

For G2, build a variant without slides 10–13 (a `transitions` input flag, see §5).

## 4. Interactive / visual component

None in the PDF. Diagrams are `dbrx-mermaid` (slide 5) or images; interactive explorers stay in the notebooks, reached by QR code.

## 5. Build

- **Source:** `slides/mmf-workshop.typ`, importing the template's `dbrx.typ`.
- **Template in the repo** (Decision 1): recommended a **vendored, pinned copy** in `slides/template/` — `dbrx.typ`, `fonts/`, `assets/` (the files `dbrx.typ` references) — plus `slides/template/VERSION` with the template commit. A small `scripts/update-slide-template.sh` re-copies it from the template repo (`gh api`, since it's private). Record the pin in `setup/VERSIONS.md`.
- **Command:** `slides/compile.sh` adapted from the template's: `typst compile --root slides --font-path slides/template/fonts --input commit_id=$(git rev-parse HEAD) slides/mmf-workshop.typ dist/mmf-workshop-slides.pdf`, plus `--input transitions=false` for the G2 variant.
- **CLI:** `uv run mmf-workshop build` calls it when `typst` is on `PATH`; otherwise prints "skipped slides: typst not installed" and still builds the zips. The PDF is **not** put in the course zips (Vocareum imports them as notebooks).
- **Network:** first compile downloads the three `@preview` packages; CI caches the Typst package directory.
- **Course sync:** lesson names and timings are typed in the slides; the test plan checks them against `AGENDA.py`.

## 6. Files to create / change

| File | Action |
|------|--------|
| `slides/mmf-workshop.typ` | Create — the deck |
| `slides/template/` (`dbrx.typ`, `fonts/`, `assets/`, `VERSION`) | Create — vendored template at the pinned commit |
| `slides/compile.sh`, `scripts/update-slide-template.sh` | Create |
| `slides/NOTES.md` | Create — presenter notes per slide (Decision 3) |
| `src/mmf_workshop/cli.py` | Change — optional slides step in `build` |
| `setup/VERSIONS.md`, `README.md` | Change — template pin; how to build the slides |
| `.github/workflows/slides.yml` | Optional — compile on push, upload the PDF |

## 7. Test plan

1. `slides/compile.sh` on macOS with Typst 0.14.2: PDF builds; Barlow is used (check `pdffonts`); the commit id is in the PDF keywords.
2. G2 variant (`transitions=false`) drops slides 10–13.
3. Read-through: lesson names, times and order match `AGENDA.py`; skill numbers match the MMF skill (`SKILL.md`); no claim without a source (no accuracy-gain percentages).
4. QR codes scan; the Mermaid diagram renders.
5. Projector check on 16:9; footer and page numbers readable.
6. `uv run mmf-workshop build` without `typst` installed still succeeds and says the slides were skipped.

## 8. Decisions for the reviewer

1. **How to bring the template in.** (a) **Vendored, pinned copy in `slides/template/`** — recommended: builds offline (after the package cache), no extra access for CI, and the pin is explicit. (b) Git submodule at the pinned commit — single source, but every clone and CI run needs access to the private template repo. (c) Typst Universe package — not available (the template isn't published).
2. **Footer text.** Keep the template default `©2026 Databricks, Inc. — All rights reserved`, or a workshop footer such as `Many-Model Forecasting with Genie Code — ©2026 Databricks, Inc.` (recommended: the latter, so printed pages are identifiable).
3. **Speaker notes.** The template has none. (a) **`slides/NOTES.md`**, one section per slide number — recommended, simplest. (b) Add `pdfpc`-style notes to the template upstream — reusable for other decks, but a template change.
4. **Title variant** — `title-slide(variant: "dark")` (recommended) or `"coral"`.
5. **Where the PDF lives for G2** — attached to the course in Vocareum's docs (recommended) or linked from the learner README; it is not in the notebook zips.
6. **Language** — English slides, French delivery (as for the course); a French version is out of scope unless requested.

## 9. Risks and out of scope

| Risk | Mitigation |
|------|------------|
| Template access: private repo | Vendored copy (Decision 1a); `update-slide-template.sh` documents how to refresh it |
| Template changes upstream | Pinned commit; refresh deliberately |
| First compile needs network for `@preview` packages | Build once online / cache in CI |
| Slides drift from the course | Read-through against `AGENDA.py` before each delivery (test 3); build records the commit |
| Brand assets in this repo | Both repos are private; the assets come from the corporate template — don't make this repo public without removing them |

Out of scope: animations; PPTX export; a French deck; content for the planned lessons beyond the "Beyond today" slide.

## 10. References

- Template: https://github.com/lbruand-db/typst-dbrx-template — `README.md`, `CLAUDE.md`, `dbrx.typ`, `compile.sh`, `.github/workflows/compile.yml` at `3def5de`
- Typst: https://typst.app/docs/ · CLI https://github.com/typst/typst · `setup-typst` action https://github.com/typst-community/setup-typst
- Packages used by the template: `cades` (QR), `muchpdf` (PDF embedding), `mmdr` (Mermaid) on https://typst.app/universe/
- Course: `labs/Source/en_us/notebooks/AGENDA.py` (agenda and times), `SPECS/SPEC.md`, `SPECS/SPEC_INDEX.md`, `Includes/Print-Dataset-Copyrights.py`
