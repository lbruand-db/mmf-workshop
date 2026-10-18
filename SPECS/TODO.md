# TODO

 - [ ] Create visual learning tools in notebook so people can educate themselves about various important topics :
       - [x] backtesting ( the importance of multiple backtests for stability ) — *3.1 Lecture - Backtesting and Forecast Stability*
       - [x] how to choose a metric ( depending on the distribution and sparsity of the time series) — *4.2 Appendix - Choosing a Forecast Metric*
 - [ ] Maybe add an extra examples of how to incorporate : exogenous variables
 - [ ] Maybe add an extra examples of how to incorporate : hierarchical reconciliation
 - [ ] Let's add a lesson on MLOps
 - [ ] Let's add a lesson on debugging (include something on the https://github.com/databricks-industry-solutions/many-model-forecasting/tree/main/apps MMF results explorer )
 - [ ] Let's add a pdf typst presentation
 - [ ] Cold start and short histories: which series MMF's data-quality checks drop (too short, too many gaps) and the fallbacks (category-level forecast, global or foundation models)
 - [ ] Segment series before choosing models: smooth / erratic / intermittent / lumpy (ADI / CV²), route each segment to suitable models — ties into the planned 2.3 Lab (Skill 2) and 4.2
 - [ ] Scaling up 100 → 1,000 → 30,000 series: runtime and cost per series on serverless (`daily_train_1000` is loaded), shuffle partitions, `backtest_length` / `stride`, which models to drop
 - [ ] Foundation models in depth: zero-shot Chronos / TimesFM / Moirai vs statistical and ML models — where they win (short or noisy series); needs GPU, so instructor-led, with the precomputed Chronos-Bolt results as the CPU fallback
 - [ ] Choosing the forecast granularity: daily vs weekly vs monthly, item vs item × store — temporal aggregation for intermittent series (MMF ships weekly / monthly configs); possibly an interactive widget like 3.1 / 4.2
