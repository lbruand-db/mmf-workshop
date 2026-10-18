# SPEC — Hierarchical Reconciliation

| | |
|---|---|
| **TODO item** | "Maybe add an extra examples of how to incorporate: hierarchical reconciliation" |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson** | M04 · 4.5 Appendix - Hierarchical Reconciliation (Skill 6) |
| **Type / time** | Appendix; optional; 20 minutes |
| **Compute** | Single Node classic cluster (serverless not supported by hierarchicalforecast) |

## 1. Goal and learner outcomes

Participants understand why independent per-level forecasts in a hierarchy create inconsistencies, and how to apply reconciliation methods to ensure coherence — store forecasts sum to region, region to state, etc. They explore MinTrace, BottomUp, and TopDown methods on M5 data and see how choice of method affects forecast quality and coherence.

By the end of the lesson, learners can:
- Explain the post-reconciliation property: child forecasts sum to parent forecasts across all levels.
- Recognize the hierarchy in their data (item → dept → category → store → state).
- Choose and apply a reconciliation method appropriate to their hierarchy size and confidence in residuals.
- Validate coherence with a simple SQL test (sums match within rounding).

## 2. Background — what MMF supports (verified, with source refs)

**MMF Skill 6 — Hierarchical Reconciliation:**
Databricks' MMF implements reconciliation via the `mmf_sa.run_reconciliation_multilevel` function, which wraps Nixtla's `hierarchicalforecast` library. Skill 6 ([upstream 6-hierarchical-reconciliation.md](https://github.com/databricks-industry-solutions/many-model-forecasting/blob/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4/skills/databricks-skills/many-model-forecasting/6-hierarchical-reconciliation.md)) orchestrates the full workflow: discover levels, confirm membership table, generate a reconciliation notebook from a template, run it on classic compute, and validate the output.

**Supported reconciliation methods:**
- **MinTrace** (default, recommended): Minimizes forecast error variance by estimating covariance from backtest residuals. Sub-methods: `mint_shrink` (default), `wls_struct`, `wls_var`, `mint_cov`. Reference: [Wickramasuriya et al., 2019](https://robjhyndman.com/papers/MinTrace.pdf).
- **BottomUp**: Sums leaf forecasts upward to all parent levels. Simple, robust, no residual requirement; understates uncertainty at aggregates.
- **TopDown**: Distributes root forecast downward using historical proportions. Good when leaf data is noisy; may underestimate leaf variance.
- **MiddleOut**: Anchors at an intermediate level, uses BottomUp up and TopDown down. Useful when a middle level is most reliable.
- **ERM** (Error Reconciliation Matrix): Learns optimal reconciliation weights from residuals. Data-hungry; works well with many backtest windows.

**Inputs to Skill 6:**
- N level-specific forecast pairs: `{level}_best_models` + `{level}_evaluation_output` tables from Skill 3–4 (3.3 Lab Provision, 3.2 Demo / 3.3 Lab Execute) run once per hierarchy level.
- `{use_case}_hierarchy_membership` table (adjacency list): `unique_id`, `level_name`, `parent_unique_id` (NULL for root).

**Outputs:**
- `{use_case}_reconciliation_output` table with columns: `unique_id`, `ds`, `y_base` (pre-reconciliation), `y_reconciled` (post-reconciliation), `hierarchy_level`, `reconciliation_method`.

**Constraints:** 
- Single Node classic cluster only (scipy sparse matrices not available on Spark Connect/serverless). 
- Compute: 1–2 hours for ~10k leaf series + MinTrace; larger hierarchies may need `wls_struct`.
- Workshop scope: demo only (no learner execution, too slow for the session).

## 3. Proposed content (section-by-section outline)

### 3.1 Overview (1 min)
Brief motivation: retail hierarchy (item → dept → category → store → state) exists in M5 and many customer datasets. Independent forecasts at each level don't sum. Reconciliation enforces aggregation rules — a planner can use parent forecasts for resource planning, leaf forecasts for inventory, confident they cohere.

### 3.2 The M5 Hierarchy (2 min)
- **Leaves (finest granularity):** item × store (unique_id = e.g. `FOODS_1_001_CA_1`, 100 sampled in the workshop)
- **Levels (coarser):** item × {dept, category, store, state}, aggregates of leaves
- **Non-leaf membership:** e.g., `FOODS_1_001_*_*` (all stores for item FOODS_1_001) → item aggregates
- Visual: simple tree diagram (SVG or Includes/ image)
- Data: `m5_static_features` (item_id, dept_id, cat_id, store_id, state_id) to build membership via groupby

### 3.3 Why Reconciliation Matters (3 min)
- Scenario: store forecast = 100, item forecast (sum of stores) = 250. Planner's dilemma.
- Root cause: each level's models were trained independently on that level's data; no cross-level consistency constraint.
- Solution: post-forecast adjustment that preserves **base forecasts** at the granular level but adjusts aggregates to sum correctly.
- Trade-off: adjustment magnitude vs. fidelity to model outputs (MinTrace vs. BottomUp).

### 3.4 Reconciliation Methods (8 min, interactive demo)
Interactive choice widget (HTML or collapsible sections) showing method behavior on a small example:

**Example data:** 2-level hierarchy (leaf, parent)
- 4 leaves, 1 parent
- Pre-reconciliation: leaf forecasts [10, 15, 12, 8], parent forecast [60] (should sum to 45)
- Show outputs for each method:

| Method | Leaf outputs | Parent output | Strategy | Cost |
|--------|------------|---------------|----------|------|
| MinTrace | [10.3, 15.2, 12.1, 8.4] | [46.0] | Optimal shrinkage from residuals | High (residual covariance) |
| BottomUp | [10, 15, 12, 8] | [45] | Leaves fixed, aggregate sums up | Low (arithmetic) |
| TopDown | [13.3, 20, 13.3, -1.3] | [60] | Root fixed, distribute down (can go negative!) | Low (proportions) |
| MiddleOut (mid=leaf) | [10, 15, 12, 8] / [45] | Same as BottomUp | Anchor at leaf, push up | Medium |

Link to Nixtla [`hierarchicalforecast` docs](https://nixtla.github.io/hierarchicalforecast/) for method details.

### 3.5 Building the Membership Table (4 min)
SQL walkthrough: turn `m5_static_features` into M5 hierarchy membership for multi-level reconciliation.
- Group by (item, dept, cat, store, state) with different granularities
- Build adjacency list: (item_store leaf → item parent), (item parent → dept parent), etc.
- Example query (pseudo-code):
  ```sql
  -- Leaf level (item × store)
  SELECT unique_id, 'item_store' AS level_name, item_parent AS parent_unique_id
  FROM (SELECT CONCAT(item_id, '_', store_id) AS unique_id, item_id AS item_parent, ...)
  UNION ALL
  -- Item level (item × all stores) as parent
  SELECT item_id, 'item', dept_id AS parent, ...
  ```

### 3.6 Running Reconciliation with Skill 6 (3 min, demo only)
Summary of the Skill 6 workflow (no hands-on in the appendix):
1. Skill 1–5 run on each level independently.
2. Skill 6 discovers levels, confirms method.
3. Generates notebook, runs on Single Node, validates coherence.
4. Outputs `reconciliation_output` merged with original forecasts.

Mention: "In a production system, you'd run this nightly after retraining all levels. The reconciliation step adds minimal cost (minutes) once forecasts are ready."

### 3.7 Validation and Business Use (2 min)
Post-reconciliation spot-checks:
- SQL: `SELECT SUM(y_reconciled) FROM … GROUP BY hierarchy_level, ds` — verify aggregates sum correctly.
- Plot: base vs. reconciled forecasts by level (box plot or line chart) — show adjustment magnitude.
- Lesson: "MinTrace typically adjusts <5% on stable hierarchies; BottomUp/TopDown preserve leaves exactly but may break upper-level credibility."

## 4. Interactive / visual component (if any: design, controls, what it demonstrates) — or "none"

**HTML/SVG widget: "Reconciliation Method Explorer"**

Simple, self-contained HTML/JS notebook cell (no external libs):
- Dropdown: select a reconciliation method (MinTrace, BottomUp, TopDown, MiddleOut)
- Inputs: leaf forecasts [f1, f2, f3, f4], parent forecast [fp], optional method parameters (mint shrink α)
- Output table: method output for leaves and parent
- Visualization: bar chart comparing base vs. reconciled at each level; shows adjustment vectors

Example: "BottomUp" → leaves stay, parent sums up. "TopDown" → parent stays, leaves reweight down. Interactive highlighting shows which values moved.

Alternative (lower effort): collapsible `<details>` blocks per method with static example.

## 5. Data, setup and runtime

**Tables used:**
- `mmf.m5.daily_train_100` (leaves: 100 item-store series)
- `mmf.m5_static_features` (item, dept, cat, store, state metadata)
- Output tables from 3.2 Demo / 4.1 Lab (if running on multi-level forecast): `{use_case}_best_models` and `{use_case}_evaluation_output` per level

**Setup changes:**
- Add `m5_hierarchy_membership` table to `mmf.m5` schema (computed once, read-only). Schema: `unique_id`, `level_name`, `parent_unique_id`.
  - For single-level demo (leaves only): not needed; appendix shows how to build it for multi-level extension.
  - For multi-level demo (item, dept, category, store, state): compute in `setup/workspace_setup.py` or in the appendix itself (SQL; ~1 min).

**Runtime:**
- Classroom setup: ~2 min (load tables).
- Reconciliation (demo/reference): Single Node memory-optimized instance (e.g., AWS `r6id.2xlarge`, 64 GB), ~5 min for 100 series.
- In production: 1–2 hours for ~10k leaves + full backtest residuals (noted as out of scope).

**Estimated learner time:** 15–20 min (demo + SQL + interactive widget).

## 6. Files to create / change

1. **New notebook:** `labs/Source/en_us/notebooks/M04 - Evaluating and Selecting Models / 4.5 Appendix - Hierarchical Reconciliation.py`
   - Overview, hierarchy explanation, method comparison, membership SQL, validation checks
   - Includes reference reconciliation output merged with forecasts
   - *Check your work* cell: verify `reconciliation_output` row count matches expected series

2. **New interactive widget (Includes):** `labs/Source/en_us/notebooks/Includes/_reconciliation_explorer.py`
   - Self-contained HTML/JS reconciliation method selector + visualizer
   - Called by `displayHTML(...)` in the appendix

3. **Setup change:** `setup/workspace_setup.py`
   - Add step to compute and stage `m5_hierarchy_membership` table in `mmf.m5` schema
   - Populate from `m5_static_features` via SQL (item, dept, category, store, state levels, fully specified hierarchy)

4. **Setup change:** `setup/VERSIONS.md`
   - Pin `hierarchicalforecast` version if not already pinned (verify in `mmf_sa` requirements)

## 7. Test plan (e2-demo and/or Vocareum; what to check)

**Dry run (G1, instructor laptop):**
1. Open the 5.1 Appendix notebook; Classroom setup runs (loads hierarchy table, reference reconciliation output).
2. Run the reconciliation method comparison widget; interact with dropdowns, verify outputs.
3. Run SQL validation queries; confirm sums are correct (within float rounding).
4. *Check your work* cell: PASS.

**Vocareum (G2, learner self-paced):**
1. Same as above on `daily_train_100` (pre-computed reference).
2. Appendix mentions "To reconcile your own multi-level forecasts, run Skill 6 — here are the steps." (no execution needed in self-paced).

**Smoke test (02_validate_env.py):**
- Verify `m5_hierarchy_membership` exists and has correct structure.
- Verify `reconciliation_output` reference table exists.

## 8. Decisions for the reviewer

1. **Scope of reconciliation in the workshop:** Should the appendix stay read-only + demo, or also include a learner exercise (run Skill 6 on a pre-prepared 2-level subset)? 
   - **Recommended:** Read-only + demo. Skill 6 requires Single Node classic compute (untested on Vocareum; the Course Vending app has an "Auto-create personal cluster" option, but whether it works there needs validation). For G1 (instructor-led), the appendix can reference an optional full run. For G2 (self-paced), keep as reference; full execution moves to G3 MLOps module (where production reconciliation fits).

2. **Hierarchy depth:** Should the membership table represent the full M5 hierarchy (item → dept → category → store → state, ~5 levels) or a simpler 2–3 level subset to keep the demo digestible?
   - **Recommended:** Full 5-level hierarchy in the membership table, but the method comparison widget and SQL demos use a small 2-level example for clarity. Learners interested in their own hierarchy can construct it from their static features by analogy.

3. **Interactive widget vs. static tables:** Is a dynamic method-comparison widget worth the HTML/JS effort, or should the appendix use static tables + prose?
   - **Recommended:** Static tables for robustness (simpler for Vocareum HTML rendering, no JS dependencies). Interactive widget is a nice-to-have for future iterations if engagement metrics show interest.

4. **Reference reconciliation output:** Should the appendix include a pre-computed reconciliation output (using BottomUp or MinTrace on reference forecasts) for learners to inspect?
   - **Recommended:** Yes, merge it into the lesson so learners can query and visualize it without waiting. Label it clearly as "pre-computed for this lesson" so they don't confuse it with their own runs.

## 9. Risks and out of scope

**Risks:**
- Single Node classic compute availability on Vocareum is untested; if the Course Vending "Auto-create personal cluster" option works, learners can run Skill 6 hands-on in G2. Otherwise, G2 execution is reference-only, with G1 (instructor-led) demonstrating the full workflow.
- `hierarchicalforecast` version compatibility: pin in setup/VERSIONS.md and verify against the pinned MMF SHA.
- Learners forget to include all hierarchy levels; reconciliation will fail silently with cryptic errors. Mitigation: *Check your work* SQL validates membership table structure.

**Out of scope:**
- Advanced reconciliation (e.g., probabilistic reconciliation, quantile coherence): outside the 2-hour workshop scope; reference papers in Notes.
- Very deep hierarchies (>10 levels) or millions of leaves: compute costs balloon; briefly mention scaling strategy (wls_struct vs. MinTrace) but don't demo.
- Auto-tuning reconciliation method per hierarchy: not in MMF Skill 6; learners choose manually.

## 10. References

- **Hierarchical Reconciliation overview:** [Wickramasuriya et al., 2019, "Optimal Forecast Reconciliation for Hierarchical and Grouped Time Series"](https://robjhyndman.com/papers/MinTrace.pdf)
- **Nixtla `hierarchicalforecast` library:** https://nixtla.github.io/hierarchicalforecast/
- **MMF Skill 6 source:** [`6-hierarchical-reconciliation.md`](https://github.com/databricks-industry-solutions/many-model-forecasting/blob/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4/skills/databricks-skills/many-model-forecasting/6-hierarchical-reconciliation.md)
- **M5 dataset & hierarchy:** https://www.kaggle.com/c/m5-forecasting-accuracy
- **MMF reconciliation implementation:** `mmf_sa.run_reconciliation_multilevel` (source: [`many-model-forecasting` repo](https://github.com/databricks-industry-solutions/many-model-forecasting/tree/322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4))
