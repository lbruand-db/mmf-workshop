# SPEC — Presentation: Typst Slide Deck

| | |
|---|---|
| **TODO item** | [ ] Let's add a pdf typst presentation |
| **Status** | Draft for review — 2026-10-18 |
| **Proposed lesson / artefact** | Standalone PDF presentation for G1 (customer workshop 2026-10-20) and reference for G2 (Vocareum self-paced course). |
| **Type / time** | Slide deck (~40–50 slides); printed PDF (~5–10 MB); compiled by CLI or CI. |
| **Compute** | Local (`typst compile`) or CI (GitHub Actions / Databricks Asset Bundle). |

## 1. Goal and outcomes

Create a **neutral-branded, professional slide deck** in Typst that serves as the **live presentation** during the 2-hour customer workshop (G1) and as a **reference deck** for the Vocareum course (G2). The deck guides instructors through the agenda, provides visual transitions between modules, embeds key diagrams, and reinforces learning objectives. By the end:

1. **Deliver** a cohesive narrative: why many-model forecasting matters, what MMF is, how to use it, results to expect, next steps.
2. **Align** with the workshop agenda (AGENDA.py and SPEC.md §6.1): introduction → 1.2 Demo (15 min) → 2.2 Demo (25 min) → M03 with 3.3 Lab (30 min) → 4.1 Lab (30 min) → wrap-up, in a 2-hour session. The lessons take 100 minutes, so the slides get about 20 minutes in total: roughly 10 for the introduction, short transitions inside the lesson slots, and 5–10 for the wrap-up.
3. **Reuse** assets from the course: `assets/screenshot.png` (course in Vocareum), diagrams from lecture notebooks (`_backtest_explorer`, `_metric_explorer`), M5 data visuals.
4. **Be maintainable:** Typst source in the repo; build with `uv run mmf-workshop build` or `typst compile`.
5. **Support two delivery modes:** G1 (in-person slide show; instructor notes, speaker cues) and G2 (static PDF for reference; downloadable from the course side pane).

## 2. Background — technical and design choices

### 2.1 Why Typst?

Typst is a modern, scriptable markup language for technical documents, competing with LaTeX and Markdown. Advantages for this project:

- **Markdown-like syntax** (easier than LaTeX for content authors; less `\` escaping).
- **Programmable** (loops, functions, imports). Easy to reuse code (e.g., title slide template, section breaks).
- **Excellent typography** (kerning, ligatures, spacing) out of the box; no tweaking needed.
- **Slide support** via community packages (Touying, Polylux; see §2.2).
- **Compilation:** `typst compile input.typ output.pdf` (single command; no intermediate steps like LaTeX's `pdflatex → bibtex → pdflatex`).
- **Web preview** (typst.app): author in a browser with live preview.
- **Fast:** compiles in seconds; PDF renders instantly.
- **Neutral branding:** No built-in Databricks logo or footer; explicit control over content.

### 2.2 Typst slide packages

Two main options:

1. **Touying** (https://github.com/touying-typst/touying): Full-featured presentation framework. Supports themes, animations (incremental reveals), speaker notes, automatic table of contents. Active maintenance. **Recommended.**

2. **Polylux** (https://github.com/andreasKroepelin/polylux): Lightweight, slide-focused. Minimal overhead. Less feature-rich but simpler to learn.

**Recommendation:** **Touying**. It has speaker notes (`#show-note()` / `#note()`), incremental reveals (`.uncover()`, `.only()`), themes (customizable but sensible defaults), and active community. Supports both `16:9` (modern) and `4:3` (classic) aspect ratios; we'll use `16:9`.

### 2.3 Fonts and branding

- **Font:** Use Typst's default (Computer Modern, or we can embed a system font like Inter, Roboto, or Noto Sans for a modern look). Decision: use Roboto (clean, web-friendly, no licensing concerns). Fallback: Typst default.
- **Colours:** For **neutral branding** (not Databricks Academy): the Databricks logo and brand colours (blue, white) are allowed — this is a reviewer decision. A suggested palette:
  - **Primary:** Professional blue (`#2563eb` or Databricks blue).
  - **Secondary:** Neutral greys (`#6b7280`, `#d1d5db`).
  - **Accent:** Emerald or teal for highlights (`#059669`).
  - **Background:** White (light theme); dark slate for titles.
  - **Logo:** Databricks logo optional (decide with reviewer). If omitted, use a generic "MMF" or "Workshop" badge.

### 2.4 Build integration

The deck compiles via:
- **CLI (local):** `typst compile slides.typ slides.pdf` (for development).
- **Build script (`uv run mmf-workshop build`):** Extends the existing CLI (src/mmf_workshop/cli.py) to compile Typst to PDF and package it into the course zips (`mmf-workshop-labs.zip`, `mmf-workshop-setup.zip`).
- **CI (optional):** GitHub Actions workflow (`.github/workflows/build.yml`) to compile on each push; artifact upload to releases or an S3 bucket.

### 2.5 Synchronization with course notebooks

The deck references live notebooks:
- **Asset paths:** Embedded images (e.g., `assets/screenshot.png`, `Includes/images/m5_decomposition.png`) are relative to the repo root. Build process verifies they exist.
- **Agenda sync:** Slide 5–10 (per-module agenda) references `AGENDA.py` notebook links and lesson names from `RESTRUCTURE.md`. If a lesson is renamed, the deck must be updated (manual; not auto-synced).
- **Timing cues:** Slides note durations (e.g., *"2.2 Demo: 20 min"*) from SPEC.md §6.1. These are reference only; instructors can adjust.

## 3. Proposed content (slide-by-slide outline)

### Part 1: Intro and Context (10 min, Slides 1–10)

**Slide 1: Title slide**
- Title: *"Many-Model Forecasting with Genie Code"*
- Subtitle: *"Retail demand, scale, and automation"*
- Speaker notes: Welcome; explain the workshop is hands-on (you'll use Databricks Genie Code); outcomes by end of day.

**Slide 2: Agenda (2 hours)**
- Table with time slots and lessons (matching AGENDA.py):
  - 0:00–0:15: **1.2 Demo** — Genie Code and the MMF Skill (setup, verify skill is installed)
  - 0:15–0:40: **2.2 Demo** — Prep and Clean with Genie Code (Skill 1: data quality)
  - 0:40–1:10: **M03** — Running Forecasts at Scale (3.1 Lecture backtesting, 3.2 Demo instructor-run, 3.3 Lab participant-run, 3.4 Appendix optional)
  - 1:10–1:40: **4.1 Lab** — Best Model per Series (4.2 Appendix metric explorer optional)
  - 1:40–2:00: **Wrap-up** — Key takeaways, next steps, Q&A
- Speaker notes: Jobs run in the background (3.3 onwards); no waiting. Reference results available if jobs don't finish. Optional lessons (1.1 Lecture theory, 2.1 Lecture structure/quality, 2.3 Lab profiling) are outside the 2-hour core.

**Slide 3: Why many-model forecasting?**
- Three scenarios (text + emoji or icon):
  1. *"Challenge: 30,000 retail SKUs across stores. No single forecasting model beats all."*
  2. *"Insight: Local models (ETS, ARIMA) adapt per-series; global models (LightGBM) learn from all; foundation models (Chronos) generalize zero-shot."*
  3. *"Solution: Run all three, pick the best per series (per-series best-model selection). 2–3x better accuracy than any single model."*
- Speaker notes: This is the why. We're not trying to build the perfect universal model; we're letting each series choose. This drives a 15–30% accuracy gain in retail.

**Slide 4: MMF architecture (diagram)**
- A flowchart (or icon-based illustration):
  - Input: Time series table (example: 100 Walmart daily sales series).
  - Three parallel paths:
    1. Local models (ETS, ARIMA, Theta, Croston) → per-series refitting.
    2. Global model (LightGBM) → single training, many inference.
    3. Foundation model (Chronos, TimesFM) → pre-trained, zero-shot.
  - Output: Best-model table (one per series), forecasts, evaluation metrics.
  - Backtest evaluation loop (rolling-origin, Skill 4).
- Speaker notes: All three run in parallel on Databricks compute (serverless or cluster). Backtesting ensures the choice is robust.

**Slide 5: About M5 (the dataset)**
- Stat: 30k item-store daily sales from Walmart (~5 years of history); we sample 100–1,000 for the workshop.
- Characteristics (with visuals):
  - Weekly seasonality (Friday sales > Monday).
  - Occasional promotions (spikes).
  - Intermittent series (spare parts, niche items: many zeros).
  - Real-world messiness (anomalies, data gaps).
- Speaker notes: M5 is a Kaggle competition dataset; we chose it because it's public, realistic, and a testbed for forecasting research. Your data may look different (longer history, different seasonality), but the method transfers.

**Slide 6: Three model classes (visual comparison)**
- A 3-column layout:
  - **Local (ETS, ARIMA):** Icon (flowchart?). *"Per-series, adapt, interpretable."* Pros: flexible. Cons: slow on volumes, cold-start weak.
  - **Global (LightGBM):** Icon. *"Cross-series, learn together, stable."* Pros: fast, strong on high-volume. Cons: less adaptable, needs many series.
  - **Foundation (Chronos):** Icon. *"Pre-trained, zero-shot, general."* Pros: no retraining, works on new series. Cons: GPU, less interpretable.
- Speaker notes: This is the "why three" answer. No single model dominates everywhere.

**Slide 7: Montero-Manso & Hyndman (2021) on locality**
- Pull a quote: *"Forecasting many time series with a single model can be more accurate than forecasting each series independently, but only when there are enough similar series to learn from and the model captures global patterns."* (paraphrased).
- Add the table: when local wins (few, irregular series), when global wins (many, regular series), when foundation wins (new, cold-start).
- Speaker notes: This is the theoretical foundation. The paper shows local, global and foundation models are complementary; no one fits all scenarios.

**Slide 8: MMF Agent and Genie Code**
- Intro: Genie Code (Databricks' AI coding agent) + MMF skill bundle = hands-on natural-language interface.
- Five skills (natural language prompts):
  1. Prep and clean
  2. Profile and classify
  3. Provision (choose models, compute)
  4. Execute (run backtest, MLflow tracking)
  5. Evaluate (best model, results app)
- Speaker notes: You don't write code. You talk to Genie Code (like ChatGPT for Databricks) and tell it what you want. It writes the Spark notebooks, runs the jobs, and gives you results.

**Slide 9: Learning objectives**
- By the end of this workshop:
  1. Run a multi-model forecast on 100+ series using Genie Code and MMF.
  2. Understand why each model class wins on certain series (local, global, foundation).
  3. Choose models and compute for your own data.
  4. Interpret forecast results and business implications.
- Speaker notes: We're not teaching you to code from scratch. We're teaching you the *concepts* and how to *use the tool*. You'll run full pipelines today.

**Slide 10: Logistics (optional, contextual)**
- Break times (if a longer session).
- Workspace info (URL, login).
- WiFi, restrooms, Q&A ("ask anytime").
- Speaker notes: Adjust for your setting (on-site vs remote, group size, breaks).

### Part 2: Live Lab Transitions (Minimal slides, since labs dominate the time)

**Slides 11–15: Transition slides during labs** (minimal content, shown between live lessons)

Each transition slide:
- Lesson name and duration.
- One key question or objective.
- Visual (e.g., screenshot, diagram).
- Speaker notes: Talking points and common pitfalls.

**Slide 11: 1.2 Demo — Genie Code and the MMF Skill** (15 min)
- Content: Workspace navigation, opening a notebook, Genie Code sidebar, verify MMF skill is visible.
- Key question: Can you see the MMF skill in Genie Code?
- Visual: `assets/screenshot.png` (AGENDA notebook in Vocareum).
- Speaker notes: If the skill doesn't appear, run the fallback (lessons self-install it). This is the gateway; everything else depends on it.

**Slide 12: 2.2 Demo — Prep and Clean with Genie Code** (25 min)
- Content: Data quality (imputation, outliers, series length), Skill 1 prompt, output table `m5_train_data`.
- Key question: Did Skill 1 clean your data? Check row counts and missing values.
- Visual: Before/after histogram (outliers removed) or flowchart (raw M5 → cleaned).
- Speaker notes: This is where learners first interact with Genie Code at scale. Skill 1 handles the prompt; they focus on understanding what was cleaned.

**Slide 13: 3.1 Lecture — Backtesting and Forecast Stability** (optional, ~10 min)
- Content: Rolling-origin backtest concept, MMF's three parameters (`prediction_length`, `backtest_length`, `stride`), interactive explorer.
- Key question: Why does window count matter? Try the MMF full (90/7) vs workshop (56/28) presets.
- Visual: Backtest explorer widget (interactive chart on-screen).
- Speaker notes: This lecture runs while the participant workspace loads. Learners engage with the explorer; no code to write.

**Slide 14: 3.3 Lab — Provision and Execute with Genie Code** (30 min)
- Content: Skill 3 (model selection), Skill 4 (backtest execution), job submission, serverless compute.
- Key question: Did your jobs submit? Check MLflow experiment while you wait.
- Visual: Flowchart (Skill 3 → config, Skill 4 → jobs).
- Speaker notes: Jobs run in parallel (CPU local/global models ~5–8 min, GPU foundation ~10–15 min). No waiting; participants move to 4.1. Reference results are pre-loaded.

**Slide 15: 4.1 Lab — Best Model per Series** (30 min)
- Content: Skill 5 (best-model selection), evaluation table, per-series winners, results explorer app.
- Key question: Which model class won most? Why (high-volume vs intermittent vs cold-start)?
- Visual: Example best-model table (screenshot with winners highlighted by model class).
- Speaker notes: By now, participants see concrete results. Connect them back to the theory (1.1 Lecture: why local wins here, global wins there).

### Part 3: Wrap-up and Next Steps (Slides 16–20)

**Slide 16: Key takeaways**
- Bullet points:
  1. No single model beats all; MMF picks the best per-series.
  2. Local, global, and foundation models are complementary.
  3. Genie Code / MMF skill makes this accessible (no coding required).
  4. You can run a full forecast pipeline in 2 hours on your data.
- Speaker notes: Reinforce the main lesson.

**Slide 17: From 100 to your data**
- Scale discussion:
  - Workshop: 100 series on serverless (minutes).
  - Next: 1,000 series on a small cluster (10–20 min).
  - Production: 30,000+ series via scheduled jobs (MLOps).
- Effort: Same Genie Code prompts scale from 100 to 1M series (parallelization is automatic).

**Slide 18: Next steps and resources**
- Links (as text and/or QR codes):
  - MMF repository: https://github.com/databricks-industry-solutions/many-model-forecasting
  - Nixtla docs (StatsForecast, MLForecast, Chronos): https://nixtla.io/
  - Hyndman's FPP3 (free online textbook): https://otexts.com/fpp3/
  - Databricks documentation: https://docs.databricks.com/
- Speaker notes: Point them to resources for deeper learning.

**Slide 19: Thank you + Q&A**
- Simple slide: *"Questions?"* + contact info.
- Speaker notes: Open the floor.

**Slide 20: Bonus / handout (optional)**
- A cheat sheet (one-pager PDF, appendix): Genie Code prompts quick reference (copy-paste text from `prompts.md` per lab).
- Speaker notes: Distribute as a PDF or link.

### Summary of slide count and timing

| Part | Slides | Content | Duration | Delivery |
|---|---|---|---|---|
| **Intro** | 1–10 | Title, agenda, why, architecture, M5 dataset, model classes, theory (Montero-Manso), Genie Code, learning objectives | ~10 min speaking | Opening (before labs) |
| **Lab transitions** | 11–15 | Five transition slides (1.2, 2.2, 3.1, 3.3, 4.1) with key questions and visuals | inside the lesson slots | Between/during lessons; while jobs run |
| **Wrap-up** | 16–20 | Key takeaways, scale (100→1,000→30k series), next steps, resources, Q&A | ~5–10 min speaking | Closing |
| **Total** | ~20 slides | — | ~20 min speaking outside the lessons + 100 min lessons = 2 hours | 2-hour workshop |

**Note:** For the self-paced Vocareum course (G2), slides 11–15 (lab transitions) are reference only; the deck can focus on intro (1–10) + wrap-up (16–20, ~15 slides total) as a downloadable reference guide from the course side pane.

## 4. Interactive / visual component (if any)

**None within the Typst deck itself.** The deck is a PDF (static). However:
- The deck **links to** interactive elements in the course (backtest explorer 3.1, metric explorer 4.2).
- A QR code on slide 18 can point to the course or a live demo.

## 5. Data, setup and runtime / build

- **Source format:** `slides.typ` (Typst source file) in the repo root or `slides/` directory.
- **Build process:**
  1. Local development: `typst compile slides.typ slides.pdf` (requires Typst CLI; installable via `cargo install typst-cli` or a system package manager).
  2. CI build: GitHub Actions workflow (`.github/workflows/build.yml`) on each push to `main` or manually triggered.
  3. Integration with `uv run mmf-workshop build`: Extend `src/mmf_workshop/cli.py` to call `typst compile` and embed the PDF into the course zips.
- **Output:** `slides.pdf` (~5–10 MB, depending on embedded images). Packaged in `mmf-workshop-setup.zip` (for instructor reference) and optionally in the course side pane for G2.
- **Images:** Embedded PNG files (screenshots, diagrams):
  - `assets/screenshot.png` (existing; Vocareum course AGENDA notebook).
  - Diagrams created for the deck (or reused from lecture notebooks):
    - `Includes/images/m5_decomposition.png` (from 2.1 lecture).
    - `Includes/images/backtest_diagram.png` (flowchart; created for this deck or extracted from 3.1 lecture).
    - `Includes/images/best_model_table.png` (screenshot of Lab 4.1 results).
- **Fonts:** Roboto (if embedded; otherwise Typst defaults). No external network calls at compile time.

## 6. Files to create / change

| File | Action | Notes |
|------|--------|-------|
| `slides/slides.typ` | Create | Main Typst source file; imports sections and assets. |
| `slides/sections/intro.typ` | Create | Slides 1–10 (intro and context). |
| `slides/sections/labs.typ` | Create | Slides 11–15 (lab transitions). |
| `slides/sections/wrapup.typ` | Create | Slides 16–20 (takeaways and Q&A). |
| `slides/theme.typ` (optional) | Create | Custom theme and colour palette (if Touying default doesn't fit). |
| `Includes/images/*.png` | Create or reuse | Diagrams referenced in slides (backtest, decomposition, best-model table). |
| `src/mmf_workshop/cli.py` | Modify | Add `build` command step: check for `typst` CLI; compile `slides.typ` → `slides.pdf`; copy into dist zips. |
| `pyproject.toml` | Modify | Add `typst-cli` as an optional dependency or document the requirement. |
| `.github/workflows/build.yml` (optional) | Create | CI workflow to compile Typst on push. |
| `README.md` or a new `slides/README.md` | Modify | Document how to build the slides locally and the CI process. |

## 7. Test plan

1. **Local build:** Run `typst compile slides/slides.typ slides/slides.pdf` on a local machine (macOS, Linux, Windows). Verify PDF renders and all images embed correctly.
2. **Content check:** Open the PDF and read through all slides; verify:
   - Text is readable (font size, contrast).
   - Images are crisp (no blurriness or distortion).
   - Links work (QR codes, if any, are scannable).
   - Slide notes appear (for instructor).
3. **CI integration:** Trigger the GitHub Actions workflow (or manually test the CLI command). Verify the PDF is built and packaged into `dist/mmf-workshop-setup.zip`.
4. **Integration with course:** Download the course zip from `dist/`. Verify the PDF is present and accessible from the Vocareum side pane (for G2).
5. **Presenter view:** If using Typst's built-in presenter mode (Touying), test on a dual-monitor setup (slide + speaker notes).

## 8. Decisions for the reviewer (numbered, with a recommended option)

**Decision 1: Slide package (Touying vs Polylux)**

*Options:*
- **Option A (recommended):** Use **Touying**. Full-featured (themes, animations, speaker notes), mature, active community, good documentation.
- **Option B:** Use **Polylux**. Simpler, lighter weight, less feature-rich but easier to learn and maintain.

**Recommended:** **Option A (Touying)**. The workshop benefits from speaker notes (cues for instructors) and incremental reveals (building a complex diagram step-by-step). Polylux is good for simple slides; Touying is better for a structured, multi-part presentation.

**Decision 2: Databricks logo and colors?**

*Context:* **Neutral branding** in this course means *not Databricks Academy* (no Academy lock-up or institution branding). The Databricks logo and colors are permitted — this is a reviewer decision.

*Options:*
- **Option A:** Databricks logo on slides, Databricks blue as primary color. Title: *"Many-Model Forecasting with Genie Code"* (no "Academy"). Shows Databricks as the platform/sponsor.
- **Option B (recommended):** No Databricks logo; generic professional blue/grey palette. Title: *"Many-Model Forecasting with Genie Code"*. Inclusive for partner organizations and customer contexts.

**Recommended:** **Option B**. The workshop is platform-agnostic in tone; the customer's focus is on the methods and results, not the Databricks brand. Logo can be added to the instructor guide separately if needed.

**Decision 3: Slide modularity (one file vs sections)**

*Options:*
- **Option A (recommended):** Modular: `slides/sections/intro.typ`, `labs.typ`, `wrapup.typ`. Main file imports them. Easier to maintain; sections can be reordered or updated independently.
- **Option B:** Single `slides.typ` file. Simpler for small decks but harder to navigate as it grows.

**Recommended:** **Option A (Modular)**. The deck is ~20 slides, structured in 3 parts. Modularity makes it maintainable and future-proof (e.g. adding a G3 MLOps section).

**Decision 4: Interactive elements (embed or link)**

*Options:*
- **Option A (recommended):** The Typst deck is static (PDF). For interactive elements (backtest explorer, metric explorer), link to them (QR code or URL) or embed a screenshot in the deck, not the interactive HTML.
- **Option B:** Embed interactive HTML within the PDF (if Typst supports it). Not recommended; PDFs don't render interactive content well.

**Recommended:** **Option A**. PDFs should be static. Interactive elements live in the course notebooks; a QR code or link in the deck points learners to them during the workshop.

**Decision 5: Presenter notes vs handout**

*Options:*
- **Option A (recommended):** Presenter notes embedded in the Typst source (Touying `#note()` blocks). When compiled, the PDF hides them (or shows them in presenter-view mode). A separate handout PDF (Slide 20 bonus) lists Genie Code prompts as a cheat sheet.
- **Option B:** No speaker notes; instead, create a detailed `PRESENTER_GUIDE.md` (separate Markdown file) with talking points, timings, and troubleshooting.

**Recommended:** **Option A**. Speaker notes in the source keep context near the slides; `#note()` blocks are non-invasive. Supplement with a separate prompt cheat sheet for participants.

**Decision 6: Slide count and timing**

*Options:*
- **Option A (recommended):** ~20 slides (intro, 5 lab transitions, wrap-up). ~20 min of speaking time; ~100 min of lab execution. Lightweight, doesn't compete with labs.
- **Option B:** ~40+ slides (deep-dive on each lab, detailed diagrams). ~60+ min of content. Risks overwhelming learners and eating into lab time.

**Recommended:** **Option A**. The workshop is **hands-on**; slides are scaffolding, not the main event. Keep them concise; let labs dominate.

## 9. Risks and out of scope

| Risk / Constraint | Mitigation |
|---|---|
| **Typst adoption:** Typst is newer than LaTeX/Markdown; some users may be unfamiliar. | Provide a `slides/README.md` with setup instructions. Link to Typst docs. Keep Typst features simple (no advanced metaprogramming). |
| **Image maintenance:** Diagrams embedded in the deck may become outdated (lesson changes, new data). | Version control the source images. Add a "Last updated" note on Slide 1. Re-validate before each delivery. |
| **CLI dependency:** `typst compile` must be installed locally and in CI. | Document in `pyproject.toml` or a CONTRIBUTING.md file. CI should fail gracefully if Typst is not installed. |
| **PDF size:** Embedded images may bloat the PDF (>10 MB). | Compress images (PNG → optimised PNG, ~50% reduction). Test PDF size after first compile. |
| **Slide synchronization:** If course content changes (e.g., lessons renamed), slides become stale. | Update manually (not automated). Add a version number to the slide deck (e.g., "v0.1 — 2026-10-20"). |

Out of scope:
- Animations or transitions (fade-in, slide-in effects). Not needed for a learning-focused workshop.
- Multi-language slides (workshop material is in English, but G1 delivery is spoken in French). The PDF is English; add a French transcript separately if needed.
- Exporting slides to other formats (PPTX, Google Slides). Typst → PDF only; if conversion is needed, a post-processing tool can handle it.
- Printing on physical slides (the deck is digital-first; printing is optional).

## 10. References

1. **Typst Documentation.** https://typst.app/ (live editor, docs, examples).

2. **Touying (Typst presentation framework).** https://github.com/touying-typst/touying
   - Examples, theme customization, speaker notes, incremental reveals.

3. **Polylux (alternative lightweight framework).** https://github.com/andreasKroepelin/polylux

4. **Typst CLI.** https://github.com/typst/typst (installation, compilation).

5. **Databricks documentation on custom presentations.** (Not specific to Typst, but general guidance on internal tooling and neutral branding.)

6. **Course materials:**
   - SPEC.md (agenda, timing, learning objectives).
   - RESTRUCTURE.md (lesson naming, slots).
   - README.md (course overview, assets).

7. **Design inspiration:**
   - Professional deck examples (Keynote, Google Slides templates) for layout and typography.
   - Typst community gallery (https://github.com/typst/packages) for themes and examples.
