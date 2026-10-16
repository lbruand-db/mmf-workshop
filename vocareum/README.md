# Vocareum packaging

How to publish the MMF workshop as a Vocareum course with the **Vocareum Course Vending Machine** app (the Databricks app that creates Vocareum courses; its URL is in `SPECS/NOTES.md`). Platform docs: go/field-driven-enablement-labs, go/vocareum-lab-guidelines.

The app creates the course from a form and generates its `config.json` (**View config.json** at the top of the form). It has no per-user setup hook and no lab-end hook — see [Known gaps](#known-gaps).

## 1. Build

```bash
uv run mmf-workshop build
```

This writes to `dist/`:

| Archive | Contents | Form field |
|---------|----------|------------|
| `mmf-workshop-labs.zip` | `labs/Source/en_us/notebooks/` — the learner course | Lab Content |
| `mmf-workshop-setup.zip` | `setup/` + the course notebooks — admin setup | Workspace setup notebook |

## 2. Create the course

In the app, click **New Course** and fill in:

### Basic settings

| Field | Value | Notes |
|-------|-------|-------|
| Course Name | e.g. `MMF Workshop – test` | Must be unique in the Vocareum account |
| Max Users per Workspace | `50` | Shared data and reference results are loaded once per workspace; learners are isolated by their own schema |
| Lab Time | `4 hours` | The course is about 2 h of learner time |
| Allow lab to be stopped | **Off** | No lab-end hook cleans up learner jobs/clusters, so let the session end and be cleaned up |
| Vocareum Org | **Field Driven Enablement Labs** | Can't be moved to another org later |
| Timezone, Start / End Date | Your test window | Student access closes at the end date |
| Template | **Data Science** | Warehouse plus catalog/schema management. Avoid the *Genie Code* template for now: it adds the *Consumer* entitlement ("consumer-only access"), which may block notebooks and jobs. Genie Code itself works without it — confirm in the test |

### Advanced settings

| Section | Field | Value |
|---------|-------|-------|
| Lab Content | Mode | **Prepared archive / notebook** |
| | File | `dist/mmf-workshop-labs.zip` |
| | Entry Notebook | `AGENDA` |
| | Top-Level Folder Name | blank (defaults to the file name) |
| Workspace setup | Enable workspace setup notebook | **On** |
| | Source | Upload `dist/mmf-workshop-setup.zip` |
| | Entry | `setup/workspace_setup` |
| | Timeout (minutes) | **`120`** — the default 20 is too short: the first run loads M5, pre-computes Chronos-Bolt and runs the reference forecast (~30–45 min). It always runs as a serverless job |
| User Resources | User Catalog & Schema | Default: **user-owned schema in dbacademy catalog**. `Includes/_common` reads the learner's location from the platform's `ops.meta` table |
| | Manage Schema | On |
| | Auto-create personal cluster | Off — lessons run on serverless |
| | Auto-create SQL warehouse | Template default (not used by the lessons) |
| Metastore | Custom Catalog Name, new metastore per workspace, system schemas | Defaults |
| User Permissions | Enable Create Catalog, Manage Catalog, Secondary, PATs | Template defaults; none are needed by the lessons |
| Data Sideload | — | Empty (`workspace_setup` loads the data) |

Before clicking **Create Course**, open **View config.json** and save it as `vocareum/config.json` in this repo, so the settings are versioned.

## 3. What runs when

| Event | What runs | Does |
|-------|-----------|------|
| Workspace provisioned | `setup/workspace_setup` (serverless job, once per workspace) | Shared `mmf.m5` data, foundation and reference forecast results (`mmf.m5_reference`), skill bundle and `mmf_sa` wheel staged in `/Volumes/mmf/m5/assets`, read-only grants to `account users` |
| Lab start | Lab Content | Imports the course as `mmf-workshop-labs/` and opens `AGENDA` |
| Each lesson | `Includes/Classroom-Setup-x.y` | Prints the learner's output location and puts the lesson's inputs in place |
| Lab Time reached | Vocareum | Ends the session |

## 4. Test

1. Create the course and wait for the workspace setup job to finish (check the job run in the workspace if the lab doesn't open).
2. Install the MMF skill for your test student (see [Known gaps](#known-gaps)).
3. Open the lab as a student. `AGENDA` should open and its lesson links should work. In lesson 1.2, Genie Code should list the MMF skill, and the setup cell should print an output location from *lab platform metadata*.
4. Open each lesson cold (in any order), run its Classroom setup and *Short on time?* cells, then *Check your work*: all should PASS.
5. Run one Genie Code lesson end to end (2.2 is the quickest) to check the agent flow.

## Known gaps

- **MMF skill install (blocks Genie Code):** the app has no per-user hook, so `setup/user_setup` doesn't run. Until the install moves into the lessons' Classroom setup, run `setup/user_setup` by hand as a workspace admin, with `username` set to the student's email (comma-separated for several).
- **No lab-end cleanup:** jobs and clusters a learner creates through Genie Code (Skills 3–4) aren't deleted when the lab ends. `vocareum/scripts/python/mmf_lab_end.py` exists for platforms with a lab-end hook; here, check the workspace for leftovers after testing.
- **To verify on the first run:** that the `ops.meta` keys are `catalog_name` / `schema_name` / `username` (otherwise outputs fall back to `mmf.{user}`); that `account users` covers the students; that the serverless setup job can reach GitHub and PyPI to stage the skill bundle and build the wheel; and that the `environment_version = "4"` notebook header is honoured.

## Appendix: manual course configuration

Courses cloned and configured by hand (go/vocareum-lab-development) use a `.cfg` file instead of the app. `vocareum/courseware/mmf-workshop.cfg` is that configuration (content, `workspace_setup`, `user_setup`, admin cluster). Upload it with both archives to `/voc/private/courseware/`, the learner README `labs/Source/en_us/voc/docs/README.md` to `/voc/docs/README.md`, and `vocareum/scripts/python/mmf_lab_end.py` to `/scripts/python/`, called from the template's `lab_end.py`. Set End Lab Behavior to **Terminate**, and don't save an image.
