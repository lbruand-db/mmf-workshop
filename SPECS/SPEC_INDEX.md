# Specs for the open TODO items — index

Draft for review — 2026-10-18. One `SPEC_<NAME>.md` per unticked item in `TODO.md` (the "visual learning tools" parent line is a category; its two sub-items are done). Each spec ends with **Decisions for the reviewer**; this page gives the proposed place of every item in the course, so the specs don't compete for the same lesson numbers.

## Proposed course map

Existing lessons are unchanged; numbers already reserved in `RESTRUCTURE.md` (1.1, 2.1, 2.3) are used for the items that fit them. Everything new is **optional** — the 2-hour core (1.2, 2.2, 3.3, 4.1) is full.

| Lesson | Spec | Type | Compute |
|--------|------|------|---------|
| 1.1 Lecture — Why Many-Model Forecasting: Local, Global and Foundation Models | [SPEC_THEORY_LOCAL_GLOBAL](SPEC_THEORY_LOCAL_GLOBAL.md) | Lecture | none |
| 2.1 Lecture — Structure and Quality of Time Series (decomposition, stationarity) | [SPEC_THEORY_DECOMPOSITION](SPEC_THEORY_DECOMPOSITION.md) | Lecture + widget | none |
| 2.3 Lab — Profile and Classify Series (ADI / CV², Skill 2) | [SPEC_SEGMENTATION](SPEC_SEGMENTATION.md) | Lab + widget | Serverless |
| 2.4 Appendix — New and Short Series (cold start) | [SPEC_COLD_START](SPEC_COLD_START.md) | Appendix | Serverless |
| 2.5 Appendix — Choosing the Forecast Granularity | [SPEC_GRANULARITY](SPEC_GRANULARITY.md) | Appendix + widget | none / Serverless |
| 3.5 Appendix — Multi-Step Forecasting and Error Growth | [SPEC_THEORY_MULTISTEP](SPEC_THEORY_MULTISTEP.md) | Lecture-style appendix + widget | none |
| 4.3 Appendix — Forecast Distributions and Service Levels | [SPEC_THEORY_PROBABILISTIC](SPEC_THEORY_PROBABILISTIC.md) | Lecture-style appendix + widget | none |
| 4.4 Appendix — Combining Forecasts vs Picking a Winner | [SPEC_THEORY_COMBINATION](SPEC_THEORY_COMBINATION.md) | Appendix + widget | none / Serverless |
| 4.5 Appendix — Hierarchical Reconciliation (Skill 6) | [SPEC_HIERARCHICAL_RECONCILIATION](SPEC_HIERARCHICAL_RECONCILIATION.md) | Appendix | Single Node classic cluster |
| **M05 — Running MMF in Production** (new module) | | | |
| 5.1 Lab — The MLOps Loop: Drift, Retraining and Promotion | [SPEC_MLOPS](SPEC_MLOPS.md) | Lab | Serverless (Jobs) |
| 5.2 Appendix — Monitoring Forecast Accuracy | [SPEC_MLOPS](SPEC_MLOPS.md) | Appendix | Serverless |
| 5.3 Appendix — Debugging MMF and the Results Explorer | [SPEC_DEBUGGING](SPEC_DEBUGGING.md) | Appendix | Serverless + Databricks App |
| 5.4 Appendix — Scaling to Thousands of Series | [SPEC_SCALING](SPEC_SCALING.md) | Appendix + calculator widget | Serverless |
| **M06 — Foundation Models** (new module, GPU, instructor-led) | | | |
| 6.1 Lecture + Demo — Foundation Models in Depth | [SPEC_FOUNDATION_MODELS](SPEC_FOUNDATION_MODELS.md) | Lecture + demo | GPU (precomputed CPU fallback) |
| 6.2 Lab — Fine-Tuning a Foundation Model | [SPEC_TSFM_FINETUNING](SPEC_TSFM_FINETUNING.md) | Lab | GPU |
| — Workshop slide deck (PDF, Typst) | [SPEC_PRESENTATION_TYPST](SPEC_PRESENTATION_TYPST.md) | Artefact | — |

## Cross-cutting decisions

1. **The course map above** — accept, or reorder. In particular: a new M05 for production topics and an M06 for GPU-only foundation-model content, rather than crowding M04.
2. **Interactive widgets** follow the 3.1 / 4.2 pattern: self-contained HTML/SVG/JS, no libraries (no Plotly), seeded synthetic series, maths checked with a Node prototype before writing the lesson. Seven specs propose one; build them one at a time.
3. **Classic compute on Vocareum** (needed only by 4.5) — the Vending app has an "Auto-create personal cluster" option; whether a Single Node cluster works there is untested. Until then, 4.5 is instructor-led in G1 and read-only in G2.
4. **Slide deck** — built on the Databricks corporate Typst template ([typst-dbrx-template](https://github.com/lbruand-db/typst-dbrx-template)), so it is Databricks-branded (no Academy marks); open points are how to vendor the template and where speaker notes live (see the spec).

## Corrections applied during review

The specs were drafted in parallel, then cross-checked against each other and against the pinned `mmf_sa` source. Points fixed in that review: lesson numbers (several specs claimed 2.3, 3.1, 4.3 or 5.1), lesson names from before the restructure ("Lab 5", "Lesson 6"), Unity Catalog model *aliases* (UC has no Development/Staging/Production stages), how statistical models produce multi-step forecasts, metric choices on intermittent series (no MAPE — see 4.2), the date Moirai was disabled upstream (February 2026), and the slide deck's timing (it must fit the 2-hour agenda).
