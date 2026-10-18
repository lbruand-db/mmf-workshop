# SPEC — Fine-Tuning a Foundation Model

| | |
|---|---|
| **TODO item** | [ ] Finetuning / pretraining TimeSeriesFoundationModels (TSFM) |
| **Status** | Draft for review — 2026-10-18 (revised: APIs verified; follows *Time Series Forecasting Using Foundation Models*, Peixeiro, Manning 2025) |
| **Proposed lesson** | M06 · 6.2 Lab — Fine-Tuning a Foundation Model (optional; after 6.1) |
| **Type / time** | Lab, ~45 min (+ runtime to be measured) |
| **Compute** | GPU (instructor-led); CPU feasibility for `chronos-2-small` to be tested; precomputed results for Vocareum |

## 1. Goal and learner outcomes

By the end, learners can:
1. Explain zero-shot vs fine-tuned vs trained-from-scratch, and when fine-tuning is worth trying (6.1's comparison shows zero-shot close but not good enough, on data unlike the pretraining corpus).
2. Fine-tune Chronos-2 on M5 history with `Chronos2Pipeline.fit()` — full or LoRA.
3. Evaluate the fine-tuned model **on the same backtest windows and metrics as MMF's models**, so the comparison with zero-shot Chronos-2 and the workshop's models is fair.
4. Say why pretraining from scratch is out of reach for a workshop, and what it would take.

## 2. Background

### 2.1 What MMF does — and doesn't

- MMF runs foundation models **zero-shot only**: `Forecaster.evaluate_foundation_model` loads the pretrained checkpoint, backtests and registers it; there is no training path (`mmf_sa/Forecaster.py`).
- Checkpoints are **hard-coded** per model class in `mmf_sa/models/chronosforecast/ChronosPipeline.py` (`self.repo = "amazon/chronos-2"`, `"autogluon/chronos-2-small"`, `"amazon/chronos-bolt-small"`, …). A fine-tuned checkpoint therefore can't be selected through `active_models` without code — see Decision 3.
- MMF evaluates point forecasts (median / 0.5 quantile) and writes one row per series × model × window (`metric_value`, `forecast`, `actual` arrays) — the format this lab reproduces for the fine-tuned model.

### 2.2 Fine-tuning APIs (verified)

| Model | How | Source |
|-------|-----|--------|
| **Chronos-2** (recommended) | `Chronos2Pipeline.fit(inputs, prediction_length, validation_inputs=None, finetune_mode="full" \| "lora", lora_config=None, context_length=None, learning_rate=1e-6, num_steps=1000, batch_size=256, output_dir=…)` → returns a **new** fine-tuned pipeline. `inputs` use the same format as `predict()` (arrays, or dicts with `target`, `past_covariates`, `future_covariates`). LoRA needs `peft`; the docstring recommends a higher learning rate (e.g. 1e-5) for LoRA. | `chronos-forecasting` **v2.2.2** (the version the course already pins in `setup/VERSIONS.md`), `src/chronos/chronos2/pipeline.py` |
| Chronos-Bolt | No `fit()` in `chronos_bolt.py`; fine-tuning goes through AutoGluon-TimeSeries (see its docs) | `chronos-forecasting` v2.2.2 |
| Chronos (T5, original) | Training script `scripts/training/train.py` with a YAML config (`model_id`, `random_init: false` to fine-tune) | `chronos-forecasting` `scripts/README.md`; this is the route the book's CH05 uses. MMF decommissioned Chronos-T5 in Feb 2026 |
| TimesFM 2.5 | LoRA with HuggingFace Transformers + PEFT: `timesfm-forecasting/examples/finetuning/finetune_lora.py` (`TimesFm2_5ModelForPrediction`, default `google/timesfm-2.5-200m-transformers`, rank 4) | `google-research/timesfm` main (`e51928e`). MMF loads TimesFM through the `timesfm` package (pinned tarball), not the Transformers checkpoint, so the adapter wouldn't plug into MMF directly |
| Moirai | — | Disabled in MMF since Feb 2026 |

### 2.3 What the book contributes

M. Peixeiro, *Time Series Forecasting Using Foundation Models* (Manning, 2025; [code](https://github.com/marcopeix/TimeSeriesForecastingUsingFoundationModels)):
- **CH02** frames the three regimes with a small model (N-BEATS pretrained on M3): zero-shot, fine-tuned, trained on the target data only — and shows forecasting a different frequency. Good conceptual opener for section A, and the closest the book gets to "pretraining" (a small model, not a foundation model).
- **CH04** fine-tunes Lag-Llama; **CH05** fine-tunes Chronos-T5 with the training script (context 64, horizon 8, 500 steps, on weekly Walmart store sales) and then **cross-validates the fine-tuned model over several windows against the zero-shot one**. CH03 fine-tunes TimeGPT through its API.
- The workflow — fine-tune, then compare with zero-shot on rolling windows — is what this lab does, with the current API (`Chronos2Pipeline.fit`) and MMF's windows.
- **Copyright:** no licence file in the repository and a commercial book — cite and link; don't copy code, text or figures.

### 2.4 Why not pretraining

Pretraining a foundation model means training on a large, diverse corpus of series (Chronos was trained on public datasets plus synthetic data) with multi-GPU compute — far outside a workshop's time and budget, and with nothing to gain on 100 M5 series. The lab mentions it with CH02's small-model illustration and the Chronos training script as pointers.

## 3. Proposed content

**A. When to fine-tune (5 min).** Regimes (CH02). Start from 6.1's result: if zero-shot Chronos-2 is already as good as the baselines, stop there; fine-tune when it is close but not good enough, or when your series look unlike public data.

**B. Data without leakage (10 min).** Temporal split, the same as MMF's: fine-tune only on data **before the first backtest cutoff** (`backtest_length=56` → the last 56 days are never seen in training), then forecast each backtest window from its own history. Build `inputs` as a list of target arrays from `daily_train_100` (optionally with the 3.4 regressors as `future_covariates`).

**C. Fine-tune (10 min + runtime).** `Chronos2Pipeline.from_pretrained("amazon/chronos-2")` (or `autogluon/chronos-2-small`, matching MMF's `Chronos2` / `Chronos2Small`), then `pipeline.fit(inputs, prediction_length=28, finetune_mode="lora", learning_rate=1e-5, num_steps=…)`; save the returned pipeline to a Unity Catalog volume. Show full vs LoRA as a choice, run one.

**D. Evaluate like MMF (10 min).** For each backtest window, forecast 28 days with the zero-shot and the fine-tuned pipeline; write rows in MMF's evaluation format (`unique_id`, `backtest_window_start_date`, `metric_name`, `metric_value`, `forecast`, `actual`, `model` = `Chronos2_finetuned`) into `{out}.m6_finetune_evaluation`. Score with the 4.2 metrics (MAE / RMSE / WAPE, bias; sMAPE alongside).

**E. Compare (10 min).** Fine-tuned vs zero-shot Chronos-2 vs the workshop models (4.1 results), overall and by series profile (share of zero days). Discuss cost (measured runtime) against gain. No expected improvement is written in advance — the text reports what the run shows.

## 4. Interactive / visual component

None; matplotlib charts and SQL tables.

## 5. Data, setup and runtime

- **Data:** `mmf.m5.daily_train_100` (optionally `daily_train_1000` for more training data — a reviewer choice); regressors from the 3.4 tables for the covariate variant.
- **Model storage:** fine-tuned checkpoint in a learner volume (or `mmf.m5.assets` for the precomputed one).
- **Precomputed (Vocareum):** `setup` gains an optional step, run once on a GPU workspace, that writes `mmf.m5_reference.m6_finetune_evaluation`; 6.2 copies it when entered cold (*Short on time?*).
- **Install:** `chronos-forecasting==2.2.2` (already pinned) + `peft` for LoRA.
- **Runtime:** to be measured (§7) — not estimated here.

## 6. Files to create / change

| File | Action |
|------|--------|
| `labs/Source/en_us/notebooks/M06 - Foundation Models/6.2 Lab - Fine-Tuning a Foundation Model.py` | Create |
| `labs/Source/en_us/notebooks/Includes/Classroom-Setup-6.2.py` | Create — ensures `m6_finetune_evaluation` (from the reference when skipped) |
| `setup/02_precompute_finetune.py` | Create — GPU, optional; writes the reference rows |
| `setup/VERSIONS.md` | Change — `peft` pin |

## 7. Test plan

1. **GPU run** (e2-demo GPU or instructor workspace): fine-tune `amazon/chronos-2` with LoRA on 100 series; record runtime, GPU type and memory; evaluate on 2 windows.
2. **CPU check:** the same with `autogluon/chronos-2-small` and few steps on serverless CPU — decides whether Vocareum learners can run a small version live.
3. **Leakage check:** assert the latest training date is before the first backtest window.
4. **Format check:** `m6_finetune_evaluation` unions with MMF's evaluation table and runs through the 4.1 best-model query unchanged.
5. **Text check:** every number in the notebook comes from tests 1–2.

## 8. Decisions for the reviewer

1. **Model:** Chronos-2 via `Chronos2Pipeline.fit` (recommended — documented API, same library and version as the course, covariates supported) vs TimesFM 2.5 LoRA (works, but a second stack and not loadable by MMF).
2. **Split:** temporal, before the first backtest cutoff (recommended — same windows as MMF, fair comparison) vs holding out whole series (tests transfer to unseen series; a different question).
3. **Fine-tuned model and MMF:** (a) evaluate outside MMF in MMF's format (recommended for the lab); (b) add a small `mmf_sa` subclass whose `repo` points at the saved checkpoint so `run_forecast` can backtest and register it — cleaner, but a code extension to verify (and possibly to propose upstream).
4. **Full vs LoRA:** LoRA by default (recommended; less memory, adapter is small), full fine-tuning as a remark.
5. **Training data:** 100 series (recommended for time) or 1,000 (more signal for fine-tuning).

## 9. Risks and out of scope

| Risk | Mitigation |
|------|------------|
| No GPU on the day / on Vocareum | Precomputed rows + *Short on time?*; test 2 may enable a small CPU run |
| Fine-tuning doesn't beat zero-shot on M5 | Report it — that is a valid answer to "is it worth it?" |
| Leakage inflates the gain | Temporal split and the leakage check (test 3) |
| API drift in `chronos-forecasting` | Pinned 2.2.2 |

Out of scope: pretraining from scratch (§2.4); multi-GPU / distributed fine-tuning; serving the fine-tuned model (M05 topics); TimeGPT fine-tuning (paid API); copying book material.

## 10. References

- `chronos-forecasting` v2.2.2 (`fd53338`): `src/chronos/chronos2/pipeline.py` (`Chronos2Pipeline.fit`), `scripts/README.md` (training/fine-tuning Chronos-T5) — https://github.com/amazon-science/chronos-forecasting
- TimesFM 2.5 LoRA example: `timesfm-forecasting/examples/finetuning/finetune_lora.py` — https://github.com/google-research/timesfm
- M. Peixeiro, *Time Series Forecasting Using Foundation Models*, Manning, 2025 — https://www.manning.com/books/time-series-forecasting-using-foundation-models ; code CH02, CH04 (`CH04_finetuning.ipynb`), CH05 (`chronos_finetune.ipynb`) — https://github.com/marcopeix/TimeSeriesForecastingUsingFoundationModels
- AutoGluon-TimeSeries (Chronos-Bolt fine-tuning) — https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-chronos.html
- MMF at the pin: `mmf_sa/Forecaster.py` (`evaluate_foundation_model`), `mmf_sa/models/chronosforecast/ChronosPipeline.py` (hard-coded `repo` per class), `README.md` (Feb 2026: Chronos-2, TimesFM 2.5; Chronos-T5 and TimesFM 1.0/2.0 decommissioned)
- Course: `SPEC_FOUNDATION_MODELS.md` (6.1), 3.4 Appendix (covariates), 4.2 Appendix (metrics)
