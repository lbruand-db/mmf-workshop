# Databricks notebook source
# MAGIC %md
# MAGIC # Workspace Setup — MMF Workshop
# MAGIC
# MAGIC Runs **once per workspace, as an admin**. On Vocareum this is the
# MAGIC `workspace_setup` entry of the course `.cfg` (called with `host` / `token`).
# MAGIC For an instructor-led workshop, run it by hand before the session.
# MAGIC
# MAGIC 1. Creates the shared catalog/schema and an `assets` volume
# MAGIC 2. Stages the MMF skill bundle in the volume (read later by `user_setup`)
# MAGIC 3. Loads M5 data (`00_data_load`) and foundation reference results
# MAGIC    (`01_precompute_foundation`) — skipped if the tables already exist
# MAGIC 4. Grants learners read-only access to the shared data
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
assets_dir = f"/Volumes/{catalog}/{schema}/assets"

# COMMAND ----------

_ = spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
_ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {source}")
_ = spark.sql(f"CREATE VOLUME IF NOT EXISTS {source}.assets")
print(f"Shared location: {source}, assets: {assets_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Stage the MMF skill bundle
# MAGIC
# MAGIC Downloads the upstream repo at the pinned `mmf_ref` and copies the Genie Code
# MAGIC skill bundle and agent instructions into `{assets_dir}/skills/`.

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
    archive = tarfile.open(fileobj=io.BytesIO(resp.read()), mode="r:gz")

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

# MAGIC %md
# MAGIC ### Load shared data

# COMMAND ----------

def tables_exist(*names):
    return all(spark.catalog.tableExists(f"{source}.{n}") for n in names)

if force_reload or not tables_exist("daily_train_100", "daily_train_1000", "m5_static_features"):
    result = dbutils.notebook.run("./00_data_load", 3600, {"catalog": catalog, "schema": schema})
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
# MAGIC ### Grant learners read-only access
# MAGIC
# MAGIC Learners write to their own Vocareum managed catalog, so they only need to
# MAGIC read the shared schema. Set `allow_user_schemas=true` for an instructor-led
# MAGIC workshop, where participants write to `{catalog}.{user}` instead.

# COMMAND ----------

grants = [
    f"GRANT USE CATALOG ON CATALOG {catalog} TO `{learner_group}`",
    f"GRANT USE SCHEMA, SELECT, READ VOLUME ON SCHEMA {source} TO `{learner_group}`",
]
if allow_user_schemas:
    grants.append(f"GRANT CREATE SCHEMA ON CATALOG {catalog} TO `{learner_group}`")

for g in grants:
    spark.sql(g)
    print(g)

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({"status": "SUCCESS", "source": source, "mmf_ref": mmf_ref, "skill_files": len(staged)}))
