# Many-Model Forecasting with Genie Code

Forecast hundreds of retail time series end-to-end — data prep, model execution and evaluation — by talking to **Genie Code**, Databricks' AI coding agent, with the **Many-Model Forecasting (MMF) skill**.

**Dataset:** M5 (Walmart daily unit sales per item × store), sampled to 100 series.
**Time:** about 2 hours. The lab session lasts 4 hours; the timer at the top shows what's left.

## Learning objectives

By the end of this lab you can:

1. Explain the MMF approach: local, global and foundation models, backtesting, and best-model selection per series.
2. Drive the MMF pipeline in natural language with Genie Code, answering the agent's questions at each decision point.
3. Run statistical and machine-learning forecasts in parallel on Databricks and track them in MLflow.
4. Pick the best model for each series and explain where each model class wins.

## How this lab works

- Your workspace opens on the **`mmf-workshop`** folder. Each lab has its own subfolder.
- **Your outputs** go to your personal catalog (named after your username), in schema **`mmf`**. Every notebook prints the exact location. Nothing you do affects other learners.
- **Shared data** is read-only in `mmf.m5`.
- **Stuck, or want to skip ahead?** Run the lab's **`catchup`** notebook. It puts the lab's expected outputs in place in seconds, so you can continue with the next lab. Every lab can be started this way.
- **Check your work** with the lab's **`checkpoint`** notebook, which prints PASS or FAIL for each item.
- When you're done, click **Submit** to be graded. Grading runs the same checkpoints.

Lab numbers follow the MMF skill numbers, so they go 0, 1, 4, 5.

## Lab 0 — Setup (10 min)

1. Run `00-setup/catchup`. It creates your schema and checks the shared data.
2. Open **Genie Code** (the assistant panel) and ask: *What skills do you have access to?* You should see the Many-Model Forecasting skill and its sub-skills.
3. Run `00-setup/checkpoint`.

## Lab 1 — Prepare the data (25 min)

1. In Genie Code, type `/prep-and-clean-data`.
2. When it asks, use catalog and schema **your personal catalog / `mmf`** (shown by the Lab 0 notebook), source table **`mmf.m5.daily_train_100`**, use case **`m5`**, daily frequency, and **no** dynamic regressors.
3. Ask: *Show me the distribution of zero values across series.* Many series are intermittent (mostly zeros) — remember this for Lab 5.
4. Run `01-prep/checkpoint`. Expected output: `m5_train_data`.

## Lab 4 — Run the forecast (40 min)

1. In Genie Code, type `/provision-forecasting-resources`, then `/execute-mmf-forecast`.
2. Choose the **CPU models** only: Seasonal Naive, AutoETS, AutoTheta, Croston Optimized, TSB, and LightGBM. GPUs aren't available in this lab — foundation model results are provided in Lab 5.
3. Pick the **smallest CPU** compute option.
4. Accept a 28-day horizon, `backtest_length=90`, `stride=7`, metric sMAPE.
5. While the jobs run (about 10 min), open **Experiments** in the left menu and explore the MLflow runs.
6. Run `04-execute/checkpoint`. Expected outputs: `m5_evaluation_output`, `m5_scoring_output`.

No time to wait? Run `04-execute/catchup` instead. `04-execute/run_cpu` shows the same forecast written by hand, without the agent.

## Lab 5 — Evaluate (30 min)

1. Run `05-evaluate/catchup`. It adds pre-computed **Chronos-Bolt** (foundation model) results next to yours, picks the best model per series, and builds a leaderboard.
2. Ask Genie Code about the results, for example:
   - *Which model wins most often?*
   - *Show me series where the foundation model beats all statistical models.*
   - *What do the worst-performing series have in common?*
3. Run `05-evaluate/checkpoint`, then click **Submit**.

## Tips

- Genie Code pauses to ask you questions. Answer them one at a time; if it goes off-track, say so, or run the lab's `catchup`.
- Every notebook runs on serverless compute — no cluster to start.
- Click **End Lab** when you're finished. Your workspace objects are cleaned up automatically.
