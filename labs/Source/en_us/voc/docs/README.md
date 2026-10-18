# Many-Model Forecasting with Genie Code

Forecast hundreds of retail time series end-to-end — data prep, model execution and evaluation — by talking to **Genie Code**, Databricks' AI coding agent, with the **Many-Model Forecasting (MMF) skill**.

**Dataset:** M5 (Walmart daily unit sales per item × store), sampled to 100 series.
**Time:** about 2 hours. The lab session lasts 4 hours; the timer at the top shows what's left. You can come back afterwards to finish the forecast jobs and explore your own results.

## Learning objectives

By the end of this lab you can:

1. Explain the MMF approach: local, global and foundation models, backtesting, and best-model selection per series.
2. Drive the MMF pipeline in natural language with Genie Code, answering the agent's questions at each decision point.
3. Run statistical and machine-learning forecasts in parallel on Databricks and track them in MLflow.
4. Pick the best model for each series and explain where each model class wins.

## How this lab works

- Your workspace opens on **`AGENDA`**, in the **`mmf-workshop`** folder: it links to every lesson (one folder per module, one notebook per lesson).
- **Your outputs** go to your personal catalog (named after your username), in schema **`mmf`**. Every lesson prints the exact location. Nothing you do affects other learners.
- **Shared data** is read-only in `mmf.m5`.
- Each lesson starts with a **Classroom setup** cell. Run it first: it puts the lesson's inputs in place, so you can start any lesson without doing the previous ones.
- **Short on time?** Lessons where Genie Code builds something have a *Short on time?* cell that puts the expected output in place in seconds.
- Each lesson ends with **Check your work**, which prints PASS or FAIL for each item.

## M01 — Foundations: 1.2 Demo — Genie Code and the MMF Skill (10 min)

1. Run the Classroom setup cell. It creates your schema and checks the shared data.
2. Open **Genie Code** (the assistant panel) and ask: *What skills do you have access to?* You should see the Many-Model Forecasting skill and its sub-skills.
3. Run *Check your work*.

## M02 — Preparing Many Series: 2.2 Demo — Prep and Clean with Genie Code (25 min)

1. In Genie Code, type `/prep-and-clean-data`.
2. When it asks, use catalog and schema **your personal catalog / `mmf`** (printed by the setup cell), source table **`mmf.m5.daily_train_100`**, use case **`m5`**, daily frequency, and **no** dynamic regressors.
3. Ask: *Show me the distribution of zero values across series.* Many series are intermittent (mostly zeros) — remember this for M04.
4. Run *Check your work*. Expected output: `m5_train_data`.

## M03 — Running Forecasts at Scale (40 min)

**3.1 Lecture — Backtesting and Forecast Stability** (optional, 10 min): an interactive explorer — change the backtest settings and see how stable the "best model" verdict is. Good to open while your jobs run.

**3.3 Lab — Provision and Execute with Genie Code**

1. In Genie Code, type `/provision-forecasting-resources`, then `/execute-mmf-forecast`.
2. Choose these **CPU models** only: Seasonal Naive, AutoETS, Croston Optimized, TSB, and LightGBM. GPUs aren't available in this lab — foundation model results are provided in 4.1.
3. Pick the **smallest CPU** compute option.
4. Ask for a 28-day horizon, **`backtest_length=56`, `stride=28`**, metric sMAPE.
5. The jobs take 10–20 minutes. **Don't wait:** glance at **Experiments** in the left menu, run the *Short on time?* cell, and move on to M04. Come back to your own results later.
6. Run *Check your work*. Expected outputs: `m5_evaluation_output`, `m5_scoring_output`.

**3.2 Demo — MMF with mmf_sa** is the instructor's demo: the same forecast written directly in Python, without the agent.

## M04 — Evaluating and Selecting Models: 4.1 Lab — Best Model per Series (30 min)

1. Run the notebook. It adds pre-computed **Chronos-Bolt** (foundation model) results next to yours, picks the best model per series, and builds a leaderboard.
2. Ask Genie Code about the results, for example:
   - *Which model wins most often?*
   - *Show me series where the foundation model beats all statistical models.*
   - *What do the worst-performing series have in common?*
3. Run *Check your work*.

**4.2 Appendix — Choosing a Forecast Metric** (optional, 10 min): an interactive explorer — see which forecast each metric selects as series get sparser or spikier, and re-score the workshop's results with other metrics.

## Tips

- Genie Code pauses to ask you questions. Answer them one at a time; if it goes off-track, say so, or use the lesson's *Short on time?* cell.
- Every notebook runs on serverless compute — no cluster to start.
- Click **End Lab** when you're finished. Your workspace objects are cleaned up automatically.
