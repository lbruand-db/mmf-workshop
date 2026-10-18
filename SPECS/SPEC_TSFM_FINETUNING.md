# SPEC — Fine-tuning Foundation Models

| | |
|---|---|
| **TODO item** | Finetuning / pretraining TimeSeriesFoundationModels (TSFM) |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | 6.2 Lab — Fine-Tuning a Foundation Model (elective, M06 module) |
| **Type / time** | Lab; elective; ~30–45 minutes hands-on + 15 min background |
| **Compute** | GPU (instructor-led G1 only); serverless CPU (reference-only path for G2) |

## 1. Goal and learner outcomes

By the end of this lesson you can:

- Explain why a pre-trained foundation model (Chronos-2, TimesFM 2.5) may underperform on your domain and when fine-tuning helps.
- Identify the data and compute trade-offs: how much M5 data is enough to improve over zero-shot?
- Fine-tune Chronos-2 on a subset of M5 (or your own data) using the `chronos-forecasting` library, outside MMF.
- Compare zero-shot vs fine-tuned results in the MMF evaluation framework.
- Know when pretraining from scratch is (and isn't) practical.

## 2. Background — what MMF supports

**MMF itself has no training path for foundation models:** `mmf_sa`'s `run_forecast()` method performs **inference only** on pre-trained or user-supplied fine-tuned models. Foundation models (Chronos-Bolt Tiny/Mini/Small/Base, Chronos-2, Chronos-2-Small, Chronos-2-Synth, TimesFM-2.5) are registered in Unity Catalog. MMF evaluates the **median** of sampled forecasts, so only point forecasts are stored in evaluation tables. There is no training step during the backtest.

**Fine-tuning outside MMF is possible:**

- **Chronos-2** (Amazon): The `chronos-forecasting` library (GitHub: amazon-science/chronos-forecasting) provides a `finetune()` API with both **LoRA** (default, memory-efficient) and **full fine-tuning** options. AutoGluon-TimeSeries also wraps this with configurable `fine_tune_mode="lora"` and `fine_tune_lr=1e-5`. Fine-tuning requires a GPU (tested on NVIDIA A10G, ~4 GB VRAM for LoRA) and typical runs take 5–10 minutes on 200 series.
- **TimesFM 2.5** (Google): The `timesfm` library (GitHub: google-research/timesfm) supports LoRA fine-tuning via HuggingFace Transformers and PEFT. Example: `google-research/timesfm/examples/finetuning/finetune_lora.py`. Requires GPU; raw data (no external normalization, as TimesFM applies RevIN internally).
- **Moirai** (Salesforce): Currently disabled in MMF (since February 2026, per the upstream README). Unofficial fine-tuning procedures exist but are not publicly documented in the uni2ts repository.

**Why pretraining from scratch is out of scope:**

Pretraining foundation models (e.g., training Chronos-2 from scratch on 1M+ series) requires multi-GPU setups and weeks of compute. It is beyond the scope of a workshop and belongs in a research or advanced MLOps context, not in a forecasting course.

## 3. Proposed content

### A. Why fine-tune? (5 min, no code)

- **When zero-shot fails:** short histories, niche domains, domain shift (e.g. manufacturing lead times vs retail sales). M5 is clean retail data, so Chronos-2 performs well; your data may not.
- **The trade-off:** fine-tuning costs GPU time and requires representative training data (at least 100–500 series; diminishing returns above 5,000). If your data is similar to the pretraining distribution, zero-shot is faster and often competitive.
- **Benchmarks:** show results from the Chronos papers (GIFT-Eval, other benchmarks) where domain-specific fine-tuning improves MAPE/sMAPE by 10–30% on specific datasets.

### B. Data preparation for fine-tuning (10 min, code)

Same as lesson 2.2 (data quality checks, imputation, anomaly capping), but:

- Use a **subset of M5** (e.g., 200 series from one state or department) as your fine-tuning dataset.
- Alternatively: upload a learner's own dataset (few hundred series) if Vocareum or instructor workspace allows external data uploads.
- **Hold out a test set:** take series 180–200 from the subset as a hold-out; train on 1–179. Foundation models are often evaluated on hold-out, not backtests.

**Classroom setup cell** copies the subset into a fine-tuning table.

### C. Fine-tune Chronos-2 with `chronos-forecasting` (15–20 min, code)

A step-by-step notebook cell:

1. **Install and imports:**
   ```python
   from chronos import Chronos
   import torch
   ```

2. **Load the pretrained model:**
   ```python
   model = Chronos.from_pretrained("amazon/chronos-2-context-large")
   ```

3. **Prepare data:** convert the M5 subset to the library's format (list of 1D arrays or a dictionary per series).

4. **Fine-tune with default settings:**
   ```python
   finetuned_model = model.finetune(context_data)
   ```
   Typical runtime: ~5 min on 200 series with GPU.

5. **Save the model** to a temporary location (local disk in a Databricks runtime, or to a volume).

### D. Forecast with the fine-tuned model (10 min, code)

- Generate forecasts on the hold-out test set (the 20 series you held back).
- Convert to MMF's evaluation format (forecast DataFrame with columns: `unique_id`, `ds`, `forecast`, `metric`).
- Compare with the zero-shot Chronos-2 forecasts from lesson 6.1 (or reference results from `mmf.m5.reference_evaluation_output`).

### E. Analyze: zero-shot vs fine-tuned (5–10 min, analysis)

- **Metric wins:** which metric (sMAPE, MAPE, MAE) shows improvement? By how much?
- **Series breakdown:** are some series helped more than others? (e.g., seasonal series vs intermittent).
- **Cost-benefit:** time and GPU cost to achieve this lift. Is it worth it for your use case?
- **Limitations:** the fine-tuned model is specific to your domain; how does it generalize to new stores or items you haven't seen?

## 4. Interactive / visual component

None required. Optional: an interactive comparison widget (similar to 4.2) showing zero-shot vs fine-tuned sMAPE per series, filterable by category.

## 5. Data, setup and runtime

**Input tables:**
- `mmf.m5.daily_train_100` or a subset (200 series from one department/state).
- Hold-out: series 180–200 (deterministic seed, not random, so it's reproducible).

**Intermediate:**
- Fine-tuned model checkpoint (saved on local Databricks driver or volume; ~2–3 GB for Chronos-2-Large).

**Output:**
- `{user_schema}.fine_tuned_evaluation`: forecasts from the fine-tuned model on the hold-out set, with sMAPE / MAPE / MAE.
- `{user_schema}.finetuning_comparison`: join of zero-shot (from 4.1) and fine-tuned rows, with a "winner" column.

**Compute:**
- GPU: ~5 min fine-tuning on 200 series (single A10G or T4).
- CPU (reference-only): pre-computed fine-tuned results loaded from `mmf.m5_reference.fine_tuned_evaluation`.

## 6. Files to create / change

**New files:**
- `labs/Source/en_us/notebooks/M04 - Evaluating and Selecting Models/4.3 Lab - Fine-tuning Foundation Models.py` — the lesson notebook.
- `labs/Source/en_us/notebooks/Includes/Classroom-Setup-4.3.py` — loads the fine-tuning subset and checkpoint reference results.

**Modified files:**
- `setup/01_precompute_foundation.py` — add a branch to fine-tune Chronos-2 on 200-series M5 subset and save results to `mmf.m5.fine_tuned_evaluation` (runs once during workspace setup, ~10 min on GPU).

**Updated configuration:**
- `setup/VERSIONS.md` — record the `chronos-forecasting==2.2.2` (or later) version used.

## 7. Test plan

**Smoke test (Vocareum / serverless):**
- Classroom setup passes: fine-tuning subset table loads.
- *Short on time?* cell loads reference fine-tuned results, comparison cell produces a winner table.

**Instructor dry run (with GPU):**
- Fine-tune Chronos-2 on the 200-series subset: verify runtime < 10 min.
- Hold-out forecast matches expected sMAPE (within ±0.05).
- Comparison with zero-shot shows expected lift (10–30% improvement on intermittent or slow-moving series; neutral or slight degradation on fast-movers if they're well-represented in pretraining).
- Record actual runtime in `instructor_notes.md`.

**Checkpoint cell:**
- Fine-tuned evaluation table has ≥ 20 rows (one per hold-out series).
- Schema includes `unique_id`, `ds`, `forecast`, `smape`.
- Comparison table has both `zero_shot_smape` and `finetuned_smape` columns.

## 8. Decisions for the reviewer

1. **Which foundation model to feature?**
   - **Recommended:** Chronos-2 (best-documented fine-tuning API, AutoGluon integration, fastest results on M5).
   - **Alternative:** TimesFM-2.5 as a bonus comparison if time allows.
   - **Out of scope:** Moirai is currently disabled in MMF.

2. **Data for fine-tuning: all of M5 or a subset?**
   - **Recommended:** 200-series subset (fast iteration, clear improvement story, practical for a 45-min lab). Full M5 (30k series) would take hours and is not suitable for a workshop.
   - **Trade-off:** 200 series may not show dramatic improvement; learners experience the workflow, not just the results.

3. **Placement in M06?**
   - **Recommended:** Lesson 6.2 Lab (after 6.1 Lecture + Demo) in the optional M06 module. Requires GPU; G2 (Vocareum) uses pre-computed reference results only.
   - **G1 delivery:** instructor-led, live fine-tuning on 200 series (~5 min).
   - **G2 delivery:** reference-only; participants load and compare pre-tuned results.

4. **Pretraining from scratch?**
   - **Decision:** out of scope. Note as "advanced research topic" in the lesson's "Out of scope" section.

## 9. Risks and out of scope

**Risks:**
- **GPU availability:** learners may not have GPU access. Mitigated by pre-computing reference results and a serverless CPU *Short on time?* path.
- **Model size:** Chronos-2-Large (~2 GB) may not fit on some single-GPU nodes; fine-tuning may OOM. Mitigation: document the `torch.cuda.empty_cache()` best practice and recommend Chronos-2-Small or Chronos-Bolt-Small if memory is tight.
- **Fine-tuned model registration:** integrating the fine-tuned checkpoint into Unity Catalog is not covered. This is an MLOps topic (G3) and belongs in lesson 4.3 as a *future work* note.
- **Generalization:** fine-tuned models on M5 subset may not generalize well; this is intentional — the lesson shows the process, not a production deployment.

**Out of scope:**
- Pretraining from scratch.
- Hierarchical fine-tuning (fine-tuning per item, per store, etc.).
- Distributed fine-tuning across multiple GPUs or nodes.
- Integration with MLflow or model registry (see G3).

## 10. References

- **Chronos-2 and Chronos-Bolt:** amazon-science/chronos-forecasting (GitHub), `finetune()` API documentation, example notebooks. https://github.com/amazon-science/chronos-forecasting
- **TimesFM:** google-research/timesfm (GitHub). https://github.com/google-research/timesfm
- **GIFT-Eval Benchmark:** foundation model evaluation on diverse forecasting tasks. Search "GIFT-Eval forecasting" or check the Chronos paper (Ansari et al., 2024).
- **Moirai and uni2ts:** Salesforce uni2ts (GitHub). https://github.com/salesforce/uni2ts
