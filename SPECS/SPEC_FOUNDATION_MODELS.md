# SPEC — Foundation Models in Depth

| | |
|---|---|
| **TODO item** | [ ] Foundation models in depth: zero-shot Chronos / TimesFM / Moirai vs statistical and ML models — where they win (short or noisy series); needs GPU, so instructor-led, with the precomputed Chronos-Bolt results as the CPU fallback |
| **Status** | Draft for review — 2026-10-18 (revised to follow *Time Series Forecasting Using Foundation Models*, Peixeiro, Manning 2025) |
| **Proposed lesson** | M06 · 6.1 Lecture + Demo — Foundation Models in Depth (optional; M06 *Foundation Models*) |
| **Type / time** | Lecture (~20 min) + demo (~20 min) |
| **Compute** | Lecture: none. Demo: GPU (instructor-led) — or serverless CPU for the small Chronos-Bolt models, **to be verified** (§2.3) — with precomputed results as the fallback |

## 1. Goal and learner outcomes

By the end, learners can:
1. Explain what a time-series foundation model is: a large model **pretrained** on many series, used **zero-shot** on new ones, optionally **fine-tuned** (6.2).
2. Name the foundation models MMF ships at the pin and what each accepts (history only, covariates).
3. Evaluate a foundation model the way every other MMF model is evaluated — rolling-window backtests against simple baselines, on the same windows and metrics — and read the result honestly.
4. Know the levers that matter in practice: context length, covariates, model size, and compute.

## 2. Background

### 2.1 The book this lesson follows

**Marco Peixeiro, *Time Series Forecasting Using Foundation Models*, Manning, November 2025, 256 pp.** ([book](https://www.manning.com/books/time-series-forecasting-using-foundation-models), [companion code](https://github.com/marcopeix/TimeSeriesForecastingUsingFoundationModels), commit `fa12429`, 2025-12-08). For practitioners who know basic forecasting; examples in Python. What the companion notebooks cover (read from the repository):

| Chapter (repo folder) | Content | Used in this lesson as |
|-----------------------|---------|------------------------|
| CH01 | Introduction | — |
| CH02 | Transfer learning with a small model (N-BEATS on M3): zero-shot vs fine-tuned vs trained-from-scratch, and forecasting another frequency | Section A — the three regimes |
| CH03 | TimeGPT (Nixtla API): zero-shot, fine-tuning, exogenous variables, cross-validation, long horizon, anomaly detection | Mentioned only — API product, not in MMF |
| CH04 | Lag-Llama: zero-shot, **tuning the context length**, fine-tuning | Section C — context length |
| CH05 | Chronos (T5): zero-shot, cross-validation, fine-tuning with the training script, tokenisation, data augmentation | Sections B–C; fine-tuning → 6.2 |
| CH06 | Moirai: zero-shot, cross-validation, forecasting with features | Mentioned — disabled in MMF at the pin |
| CH07 | TimesFM 2.0: cross-validation, forecasting with covariates | Section C — covariates |
| CH08–CH09 | LLMs for forecasting (prompting a general LLM; Time-LLM via NeuralForecast) | Out of scope (see the capstone result below) |
| CH10 | Capstone: one daily series (blog traffic), 7-day horizon, Seasonal Naive / AutoARIMA / TimeGPT / Chronos / Moirai / TimesFM / Time-LLM | Section D — the comparison pattern |

Two lessons from the book shape this spec:
- **Evaluate with cross-validation against baselines.** Every model chapter runs rolling-window cross-validation and compares with Seasonal Naive / AutoARIMA. That is exactly MMF's backtest, so the lesson can compare foundation models with the workshop's models on equal terms.
- **No model wins by default.** In the capstone's saved output (one series, h = 7), MAE was: TimesFM 230, Chronos 239, TimeGPT 249, AutoARIMA 259, TimeGPT with exogenous features 300, Seasonal Naive 325, Moirai 328, Time-LLM 344 — and Time-LLM took 841 s on CPU. Foundation models were competitive with a well-fitted AutoARIMA, not far ahead, and one of them lost to Seasonal Naive. A single series proves nothing general; the lesson uses it as a *pattern* ("run the comparison on your data"), then does it on 100 M5 series.

The book's models are older checkpoints (Chronos-T5, TimesFM 2.0-500m, Moirai 1.0, Lag-Llama); MMF at the pin ships newer ones (below). Its data differs too: the book's Walmart data (`walmart_sales_small.csv`) is weekly store-level sales with holiday, temperature, fuel-price, CPI and unemployment columns; the course uses M5 daily item × store sales.

**Copyright.** The companion repository has no licence file and the book is commercial: link to them and cite chapters; don't copy their notebooks, text or figures into the course. All course code is written fresh on M5 with MMF.

### 2.2 What MMF supports at the pin (`322ef91`)

| Model (`active_models` name) | Accepts | Source |
|------------------------------|---------|--------|
| `ChronosBoltTiny` / `Mini` / `Small` / `Base` | history only | `models_conf.yaml` (`num_samples: 10`, `batch_size: 16`) |
| `Chronos2`, `Chronos2Small`, `Chronos2Synth` | history + `dynamic_future_*` and `static_features` covariates | `ChronosPipeline.py` (Chronos-2 forecaster "with native covariate support") |
| `TimesFM_2_5_200m` | history + covariates (via timesfm's `forecast_with_covariates`, single-GPU path); context length `context_len`, default 512 | `TimesFMPipeline.py` |
| `MoiraiSmall` / `Base` / `Large` | — | Disabled since February 2026 (upstream README: uni2ts requires torch < 2.5) |

- **Zero-shot only.** `Forecaster.evaluate_foundation_model` registers the model in Unity Catalog and backtests it; there is no training or fine-tuning path (fine-tuning → `SPEC_TSFM_FINETUNING`, 6.2).
- **Point forecasts.** Chronos-Bolt forecasts are reduced to the median (`np.median`), Chronos-2 to the 0.5 quantile; the evaluation table stores point forecasts only (quantiles → `SPEC_THEORY_PROBABILISTIC`, 4.3).
- **Same evaluation as other models.** Foundation models are backtested on the same windows (`backtest_length`, `stride`) and metric, so their rows sit next to the local and global models' in the evaluation table.
- **Install:** `mmf_sa[foundation]` (`requirements-foundation.txt`, already staged by `setup/workspace_setup`).

### 2.3 CPU or GPU — to verify

The course has assumed foundation models need a GPU (README, *Known limitations*: "`run_forecast` with `accelerator="cpu"` silently skips foundation models"). At the pinned commit that no longer holds in the code: `accelerator` only affects NeuralForecast models, Chronos loads with `device_map="cuda" if available else "cpu"`, and the upstream README says (May 2026) that all model classes run on serverless — its foundation example uses serverless **GPU** (A10, environment v5, `serverless=True`). So Chronos-Bolt *should* run on serverless CPU through MMF, only slower. **Test before relying on it** (§7, test 1): if `ChronosBoltSmall` on 100 series × 2 windows runs in a few minutes on serverless CPU, 6.1's demo becomes runnable on Vocareum; if not, keep it instructor-led with the precomputed results. Either way, correct the README line once tested.

## 3. Proposed content

**A. Pretrained, zero-shot, fine-tuned (5 min).** The three regimes (book CH02): train on your data from scratch; use a model pretrained on other data as is (zero-shot); adapt it with a little of your data (fine-tuning, 6.2). What "pretrained on many series" buys — patterns seen before — and what it can't know (your promotions, your calendar) unless you pass covariates.

**B. The models MMF ships (5 min).** Table from §2.2: Chronos-Bolt (fast, history only), Chronos-2 (covariates), TimesFM 2.5 (covariates, context length), Moirai (disabled). How they turn a forecast distribution into MMF's point forecast. Where TimeGPT and LLM-based approaches (book CH03, CH08–09) fit: outside MMF; the capstone result says they are not a shortcut.

**C. The levers (10 min).**
- *Context length* (book CH04): how much history the model reads. M5 has ~5 years of daily data; TimesFM reads 512 days by default. Longer context is not automatically better — it is a parameter to test.
- *Covariates* (book CH06–07): the 3.4 Appendix regressors (`snap`, `is_event`, `relative_price`) passed to Chronos-2 via `dynamic_future_numerical` — the same scoring-table pattern as 3.4.
- *Model size and compute*: Tiny → Base; GPU vs CPU (§2.3); cost measured, not assumed (`SPEC_SCALING`).

**D. The comparison, on M5 (20 min demo).** Follow the book's capstone pattern on 100 series instead of one: in the evaluation table, foundation models next to Seasonal Naive, AutoETS, Croston/TSB and LightGBM, same windows, using the 4.2 metrics (MAE / RMSE / WAPE and bias; sMAPE alongside, with its caveat on zero-heavy series). Break down by series profile — share of zero days (2.2, 2.3), volume — and look for where foundation models win or lose. **No expected numbers are written in advance**: the instructor dry run records them, and the lecture text is written from what the data shows. If time allows, add `Chronos2` with the 3.4 covariates and compare with `Chronos2` without.

**E. Choosing (wrap-up).** A short checklist rather than a decision tree: baseline first; compare on several backtest windows (3.1) with a metric that suits the series (4.2); try a foundation model zero-shot when history is short or new series keep appearing (cold start, 2.4); add covariates when you know the future drivers; fine-tune (6.2) only if zero-shot is close but not good enough.

## 4. Interactive / visual component

None new. Section D uses matplotlib charts and SQL tables in the notebook. (A widget comparing model classes would need real results to be honest, so it is not proposed.)

## 5. Data, setup and runtime

- **Data:** `mmf.m5.daily_train_100`; learners' or reference evaluation tables; the 3.4 regressor tables for the covariate run.
- **Precomputed fallback:** `mmf.m5.reference_evaluation_output` (Chronos-Bolt-Small on CPU, 100 series × 2 windows — from `setup/01_precompute_foundation.py`). Extend it with `Chronos2` and `TimesFM_2_5_200m` runs if a GPU workspace is available during setup.
- **Runtime:** to be measured (§7). Don't publish runtimes before measuring.

## 6. Files to create / change

| File | Action |
|------|--------|
| `labs/Source/en_us/notebooks/M06 - Foundation Models/6.1 Lecture - Foundation Models in Depth.py` | Create |
| `labs/Source/en_us/notebooks/Includes/Classroom-Setup-6.1.py` | Create |
| `setup/01_precompute_foundation.py` | Change — optionally run the foundation models through MMF (if §2.3 holds) so precomputed rows match MMF's evaluation format exactly |
| `labs/Source/en_us/instructor/Foundation Models on GPU.py` | Change — align with this lesson or fold into it |
| `README.md` (*Known limitations*) | Change after test 1 — CPU behaviour of foundation models |
| `AGENDA.py`, learner README, `SPECS/RESTRUCTURE.md` | Change — add M06 |

## 7. Test plan

1. **CPU feasibility (first):** on e2-demo serverless CPU, `run_forecast` with `ChronosBoltSmall` on `daily_train_100`, `backtest_length=56`, `stride=28`; record runtime and check the evaluation rows. Repeat with `Chronos2`. Decide the compute line in the header from this.
2. **GPU run** (instructor workspace): `Chronos2`, `TimesFM_2_5_200m`, with and without the 3.4 covariates; record runtimes.
3. **Notebook run** end to end on the precomputed results only (Vocareum path).
4. **Text check:** every number in the lecture comes from tests 1–2; no claim that a model class "wins" without a table behind it.

## 8. Decisions for the reviewer

1. **Use the book as the lesson's companion reading** (cite chapters, link the repo; no copied material) — recommended.
2. **Compute:** decide after test 1 — (a) runnable on serverless CPU with Chronos-Bolt if it is fast enough (recommended if it is), (b) instructor-led GPU demo + precomputed results.
3. **Models in the demo:** Chronos-Bolt-Small + Chronos-2 + TimesFM 2.5 (recommended); Moirai mentioned as disabled.
4. **Covariates run** (Chronos-2 with the 3.4 regressors): include if the GPU run (test 2) shows it works — recommended as the last demo step.
5. **TimeGPT and LLM-based forecasting** (book CH03, CH08–09): mention only — recommended (TimeGPT is a paid API; Time-LLM was slowest and least accurate in the book's capstone).

## 9. Risks and out of scope

| Risk | Mitigation |
|------|------------|
| M5's zero-heavy series don't show foundation models in a good light | Report what the data shows, by series profile; that is the lesson |
| CPU too slow; GPU not available on the day | Precomputed results; test 1 before committing to a live run |
| Precomputed results computed outside MMF differ in format from MMF's | Recompute them through MMF if test 1 passes |
| Book material copied by accident | Link and cite only |

Out of scope: pretraining a model; transformer internals beyond one slide; TimeGPT and LLM-based forecasting hands-on; anomaly detection (covered in the book, not in this course); fine-tuning (6.2).

## 10. References

- M. Peixeiro, *Time Series Forecasting Using Foundation Models*, Manning, 2025 — https://www.manning.com/books/time-series-forecasting-using-foundation-models ; code: https://github.com/marcopeix/TimeSeriesForecastingUsingFoundationModels (CH02–CH10 notebooks, `requirements.txt`)
- Chronos / Chronos-Bolt / Chronos-2 — https://github.com/amazon-science/chronos-forecasting
- TimesFM — https://github.com/google-research/timesfm (Das et al., "A decoder-only foundation model for time-series forecasting", ICML 2024)
- Moirai / uni2ts — https://github.com/SalesforceAIResearch/uni2ts
- MMF at the pin: `mmf_sa/models/models_conf.yaml`, `mmf_sa/models/chronosforecast/ChronosPipeline.py`, `mmf_sa/models/timesfmforecast/TimesFMPipeline.py`, `mmf_sa/Forecaster.py` (`evaluate_foundation_model`, `score_foundation_model`), `README.md` (Feb 2026 Chronos-2 / TimesFM 2.5; Moirai disabled; May 2026 serverless), `examples/serverless/foundation_serverless.ipynb`
- Course: `SPEC_TSFM_FINETUNING.md` (6.2), `SPEC_THEORY_PROBABILISTIC.md` (4.3), `SPEC_SCALING.md` (5.4), 3.4 Appendix (covariates), 4.2 Appendix (metrics)
