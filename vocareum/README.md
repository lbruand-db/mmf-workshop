# Vocareum packaging

How to publish the MMF workshop as a Vocareum course. See go/vocareum-lab-development and go/vocareum-lab-guidelines for the platform docs.

```
vocareum/
├── courseware/mmf-workshop.cfg     # → /voc/private/courseware/
└── scripts/python/mmf_lab_end.py   # → /scripts/python/, called from lab_end.py
```

The learner side-pane README lives with the course: `labs/Source/en_us/voc/docs/README.md` → `/voc/docs/README.md`.

## 1. Build

```bash
uv run mmf-workshop build
```

This writes to `dist/`:

| Archive | Contents | Used by `.cfg` key |
|---------|----------|--------------------|
| `mmf-workshop-labs.zip` | `labs/Source/en_us/notebooks/` — learner course | `content` |
| `mmf-workshop-setup.zip` | `setup/` + course notebooks — admin notebooks | `workspace_setup`, `user_setup` |

## 2. Course and part settings

Clone a course template in the **GenAI** org (serverless enabled), with **Clone by Copy**. Then set:

| Setting | Value | Why |
|---------|-------|-----|
| Lab Type | Databricks | |
| LTI | Off for direct enrolment, on for Docebo | |
| Users per workspace | As high as product limits allow | Shared data and reference results are per workspace; learners are isolated by managed catalog |
| Session Length | 240 min | Course is about 2 h of learner time |
| Budget (total time) | ≤ 720 min | At most 3× the session length |
| End Lab Behavior | **Terminate** resources | Otherwise `lab_end` doesn't run and learner jobs/clusters keep running |
| Interface | Timer on, Readme button on | Shows `docs/README.md` |
| Grading | Off | The course is not graded; each lesson's *Check your work* is learner feedback |
| Course Feedback | On | |

## 3. Upload

In **Configure Workspace → Files** (do **not** save an image — `/voc` is already persisted):

1. `/voc/private/courseware/`: `dist/mmf-workshop-labs.zip`, `dist/mmf-workshop-setup.zip`, `vocareum/courseware/mmf-workshop.cfg`.
2. `/voc/docs/README.md`: `labs/Source/en_us/voc/docs/README.md`.
3. `/scripts/python/`: `vocareum/scripts/python/mmf_lab_end.py`. In the template's `lab_end.py`, call:

   ```python
   from mmf_lab_end import reap_user
   reap_user(host, token, username)
   ```

   `host`, `token` and `username` come from however the template's `lab_end.py` receives them.

## 4. What runs when

| Hook | Notebook / script | Does |
|------|-------------------|------|
| Workspace created | `setup/workspace_setup` (admin cluster) | Shared `mmf.m5` data, foundation and Lab 4 reference results, skill bundle and `mmf_sa` wheel staged in `/Volumes/mmf/m5/assets`, learner grants. Takes about 30–45 min the first time |
| Learner added | `setup/user_setup` | Installs the MMF skill and `.assistant_instructions.md` in the learner's home folder |
| Lab start | `content` | Imports the course notebooks as `mmf-workshop/`, opens lesson 1.2 |
| Lab end | `mmf_lab_end.reap_user` | Cancels runs and deletes jobs, clusters and MLflow experiments the learner created. Vocareum drops the managed catalog itself |

## 5. Test

1. Open **Student View**. Lab 0 should open, and Genie Code should list the MMF skill.
2. Open each lesson cold (in any order), run its Classroom setup and *Short on time?* cells, then *Check your work*: all should PASS.
3. Click **End Lab**, then check from an admin session that the learner's jobs, clusters and experiments are gone.

## To verify on the first deployment

- **Admin cluster** (`admin_cluster_config`): `18.0.x-cpu-ml-scala2.13` is assumed from the MMF requirement (DBR 18 ML or later), and the cluster must be Unity Catalog-enabled for `/Volumes`. Adjust to what the Vocareum admin cluster supports.
- **Archive format:** the archives are zips of source-format notebooks, the same format a folder export produces. Check that Vocareum's `src` import accepts them.
- **`learner_group`:** `workspace_setup` grants read access to `account users`. Check that this group covers Vocareum learners.
- **Genie Code** must be enabled on the workspace. If it isn't on by default for the org, request it at go/lpt-general-request.
