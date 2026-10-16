# Pinned versions

Everything learners run is pinned and staged in `/Volumes/mmf/m5/assets/` by `setup/workspace_setup`, so lab notebooks don't download code from GitHub.

| Asset | Pin | Where it is set | Staged at |
|-------|-----|-----------------|-----------|
| MMF repo (`mmf_sa` wheel + Genie Code skill bundle) | `322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4` | `mmf_ref` widget in `workspace_setup.py` | `assets/wheels/`, `assets/skills/` (each with a `VERSION` file) |
| `mmf_sa` dependencies | Exact pins from upstream `pyproject.toml` (e.g. `statsforecast==2.0.0`, `mlforecast==1.0.31`, `lightgbm==4.6.0`), installed from PyPI | upstream | — |
| `datasetsforecast` (M5 loader, setup only) | `0.0.8` | `00_data_load.py` | — |
| M5 raw data (setup only) | Nixtla `m5-forecasts` `m5.zip` | `datasetsforecast` | `assets/m5/datasets/` — downloaded only if absent |
| `chronos-forecasting` (reference pre-compute, setup only) | `2.2.2` (same as `mmf_sa[foundation]`) | `01_precompute_foundation.py` | — |

**Known exception:** `mmf_sa[foundation]` pulls `timesfm` from a GitHub tarball (pinned to a commit upstream). Only `labs/Source/en_us/instructor/Foundation Models on GPU.py` uses it; it needs a GPU and is not in the learner course.

## Updating the MMF pin

1. Pick the new commit: `git ls-remote https://github.com/databricks-industry-solutions/many-model-forecasting.git HEAD`.
2. Update the `mmf_ref` default in `workspace_setup.py` and the table above.
3. Re-run `workspace_setup` with `force_reload=true`. The skill bundle and wheel are always re-staged; `force_reload` also recomputes the data and the `m5_reference` results with the new `mmf_sa`. Then re-run `user_setup` for existing users.
4. Re-run every lesson's *Check your work*, and re-check the golden-path prompts if the skills' gates changed.
