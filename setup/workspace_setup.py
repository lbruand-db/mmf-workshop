# Databricks notebook source
# MAGIC %md
# MAGIC # Workspace Setup — MMF Workshop
# MAGIC
# MAGIC Runs **once per workspace, as an admin**. On Vocareum this is the
# MAGIC `workspace_setup` entry of the course `.cfg` (called with `host` / `token`).
# MAGIC For an instructor-led workshop, run it by hand before the session.
# MAGIC
# MAGIC 1. Creates the shared catalog/schema and an `assets` volume
# MAGIC 2. Stages, from the upstream repo at the pinned `mmf_ref`, the MMF skill
# MAGIC    bundle (read later by `user_setup`) and an `mmf_sa` wheel (installed by
# MAGIC    the labs) — so learners never download code from GitHub
# MAGIC 3. Loads M5 data (`00_data_load`, raw files cached in the volume) and
# MAGIC    foundation reference results (`01_precompute_foundation`) — skipped if
# MAGIC    the tables already exist
# MAGIC 4. Runs the reference solution (lesson *3.2 Demo — MMF with mmf_sa*) once into
# MAGIC    `{catalog}.{schema}_reference`, so lessons can copy results instead of
# MAGIC    re-running the forecast — skipped if already present
# MAGIC 5. Grants learners read-only access to the shared data and reference results
# MAGIC
# MAGIC Safe to re-run.

# COMMAND ----------

dbutils.widgets.text("host", "")
dbutils.widgets.text("token", "")
dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("schema", "m5")
dbutils.widgets.text("learner_group", "account users")
dbutils.widgets.text("mmf_ref", "322ef91b7002067f9f7c7c37e5ca3e9e8abb28b4")
dbutils.widgets.dropdown("allow_user_schemas", "false", ["false", "true"])
dbutils.widgets.dropdown("force_reload", "false", ["false", "true"])

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
learner_group = dbutils.widgets.get("learner_group")
mmf_ref = dbutils.widgets.get("mmf_ref")
allow_user_schemas = dbutils.widgets.get("allow_user_schemas") == "true"
force_reload = dbutils.widgets.get("force_reload") == "true"

source = f"{catalog}.{schema}"
reference = f"{catalog}.{schema}_reference"
assets_dir = f"/Volumes/{catalog}/{schema}/assets"

# COMMAND ----------

_ = spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {source}")
_ = spark.sql(f"CREATE VOLUME IF NOT EXISTS {source}.assets")
print(f"Shared location: {source}, assets: {assets_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Stage the MMF skill bundle and `mmf_sa` wheel
# MAGIC
# MAGIC Downloads the upstream repo at the pinned `mmf_ref`, copies the Genie Code
# MAGIC skill bundle and agent instructions into `{assets_dir}/skills/`, and builds
# MAGIC `mmf_sa` into `{assets_dir}/wheels/` with a requirements file per model set.

# COMMAND ----------

import io
import shutil
import tarfile
import urllib.request
from pathlib import Path

skills_dir = Path(assets_dir) / "skills"
bundle_prefix = "skills/databricks-skills/many-model-forecasting/"
instructions_name = "skills/assistant_instructions.md"

url = f"https://codeload.github.com/databricks-industry-solutions/many-model-forecasting/tar.gz/{mmf_ref}"
with urllib.request.urlopen(url) as resp:
    repo_tarball = resp.read()
archive = tarfile.open(fileobj=io.BytesIO(repo_tarball), mode="r:gz")

if skills_dir.exists():
    shutil.rmtree(skills_dir)
(skills_dir / "bundle").mkdir(parents=True)

staged = []
for member in archive.getmembers():
    if not member.isfile() or "/" not in member.name:
        continue
    # Strip the "many-model-forecasting-<ref>/" top-level folder
    rel = member.name.split("/", 1)[1]
    if rel.startswith(bundle_prefix) and "/" not in rel[len(bundle_prefix):]:
        dest = skills_dir / "bundle" / rel[len(bundle_prefix):]
    elif rel == instructions_name:
        dest = skills_dir / "assistant_instructions.md"
    else:
        continue
    dest.write_bytes(archive.extractfile(member).read())
    staged.append(dest.name)

(skills_dir / "VERSION").write_text(mmf_ref)
assert "SKILL.md" in staged and "assistant_instructions.md" in staged, f"Incomplete skill bundle: {staged}"
print(f"Staged {len(staged)} skill files from {mmf_ref[:12]}: {sorted(staged)}")

# COMMAND ----------

import subprocess
import sys

wheels_dir = Path(assets_dir) / "wheels"
if wheels_dir.exists():
    shutil.rmtree(wheels_dir)
wheels_dir.mkdir(parents=True)

tarball_path = Path("/tmp/many-model-forecasting.tar.gz")
tarball_path.write_bytes(repo_tarball)
subprocess.run(
    [sys.executable, "-m", "pip", "wheel", "--no-deps", "--quiet", str(tarball_path), "-w", str(wheels_dir)],
    check=True,
)
(wheels_dir / "VERSION").write_text(mmf_ref)
mmf_wheels = sorted(wheels_dir.glob("mmf_sa-*.whl"))
assert len(mmf_wheels) == 1, f"Expected one mmf_sa wheel, got {mmf_wheels}"

# The wheel file name depends on the build backend version, so labs install
# through these stable requirements files instead of naming the wheel.
for name, extras in {"requirements-cpu.txt": "local,global", "requirements-foundation.txt": "foundation"}.items():
    (wheels_dir / name).write_text(f"mmf_sa[{extras}] @ file://{mmf_wheels[0]}\n")
print(f"Built {mmf_wheels[0]} + requirements-cpu.txt / requirements-foundation.txt")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Load shared data

# COMMAND ----------

def tables_exist(*names):
    return all(spark.catalog.tableExists(f"{source}.{n}") for n in names)

if force_reload or not tables_exist("daily_train_100", "daily_train_1000", "m5_static_features"):
    result = dbutils.notebook.run(
        "./00_data_load", 3600, {"catalog": catalog, "schema": schema, "cache_dir": assets_dir}
    )
    print(f"00_data_load: {result}")
else:
    print("M5 tables already present — skipping data load")

if force_reload or not tables_exist("reference_evaluation_output"):
    result = dbutils.notebook.run(
        "./01_precompute_foundation", 3600, {"catalog": catalog, "schema": schema, "n_series": "100"}
    )
    print(f"01_precompute_foundation: {result}")
else:
    print("Foundation reference results already present — skipping pre-compute")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Pre-compute reference Lab 4 results
# MAGIC
# MAGIC Runs the reference solution as a "reference learner" writing to
# MAGIC `{reference}`. Takes ~5–10 min on 100 series.

# COMMAND ----------

if force_reload or not all(
    spark.catalog.tableExists(f"{reference}.{t}") for t in ["m5_evaluation_output", "m5_scoring_output"]
):
    spark.sql(f"DROP SCHEMA IF EXISTS {reference} CASCADE")
    result = dbutils.notebook.run("../labs/Source/en_us/notebooks/M03 - Running Forecasts at Scale/3.2 Demo - MMF with mmf_sa", 7200, {
        "catalog": catalog,
        "source_schema": schema,
        "user_catalog": catalog,
        "user_schema": f"{schema}_reference",
        "n_series": "100",
        "run_id": "reference",
    })
    print(f"3.2 Demo - MMF with mmf_sa: {result}")
else:
    print(f"Reference Lab 4 results already present in {reference} — skipping")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Grant learners read-only access
# MAGIC
# MAGIC Learners write to their own Vocareum managed catalog, so they only need to
# MAGIC read the shared schema. Set `allow_user_schemas=true` for an instructor-led
# MAGIC workshop, where participants write to `{catalog}.{user}` instead.

# COMMAND ----------

grants = [
    f"GRANT USE CATALOG ON CATALOG {catalog} TO `{learner_group}`",
    f"GRANT USE SCHEMA, SELECT, READ VOLUME ON SCHEMA {source} TO `{learner_group}`",
    f"GRANT USE SCHEMA, SELECT ON SCHEMA {reference} TO `{learner_group}`",
]
if allow_user_schemas:
    grants.append(f"GRANT CREATE SCHEMA ON CATALOG {catalog} TO `{learner_group}`")

for g in grants:
    spark.sql(g)
    print(g)

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({"status": "SUCCESS", "source": source, "reference": reference, "mmf_ref": mmf_ref, "skill_files": len(staged)}))
