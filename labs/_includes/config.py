# Databricks notebook source
# MAGIC %md
# MAGIC # Shared lab configuration
# MAGIC
# MAGIC Included by every lab notebook via `%run ../_includes/config`. Resolves where
# MAGIC the learner **reads** shared data and where they **write** their outputs.
# MAGIC
# MAGIC | Variable | Meaning | Default |
# MAGIC |----------|---------|---------|
# MAGIC | `catalog`, `source_schema` | Shared, read-only M5 data (`source`) | `mmf`, `m5` |
# MAGIC | — | Shared, read-only reference results (`reference`) used by catchups | `mmf.m5_reference` |
# MAGIC | `user_catalog`, `user_schema` | Learner outputs (`out` = `user_catalog.user_schema`) | see below |
# MAGIC
# MAGIC **Output location:**
# MAGIC - **Vocareum:** each user gets a managed catalog named after their username
# MAGIC   (`vocuser12345@vocareum.com` → `vocuser12345_vocareum_com`), with all
# MAGIC   privileges inside it and automatic cleanup at lab end. Outputs go to
# MAGIC   `{managed_catalog}.mmf`.
# MAGIC - **Elsewhere (instructor-led workshop):** no managed catalog exists, so outputs
# MAGIC   go to `{catalog}.{user}` where `{user}` is derived from the email.
# MAGIC
# MAGIC `username` is for the grader only: `setup/autograde` runs checkpoints as an
# MAGIC admin and sets it to the learner's email so their locations are resolved.

# COMMAND ----------

import re

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("source_schema", "m5")
dbutils.widgets.text("user_catalog", "")
dbutils.widgets.text("user_schema", "")
dbutils.widgets.text("username", "")

catalog = dbutils.widgets.get("catalog")
source_schema = dbutils.widgets.get("source_schema")
user_catalog = dbutils.widgets.get("user_catalog")
user_schema = dbutils.widgets.get("user_schema")

user_email = dbutils.widgets.get("username") or spark.sql("select current_user() as user").collect()[0]["user"]


def _identifier(s: str) -> str:
    """Lower-case and replace characters not allowed in unquoted UC names."""
    return re.sub(r"[^a-z0-9_]", "_", s.lower())


if not user_catalog:
    managed_catalog = _identifier(user_email)
    if spark.sql(f"SHOW CATALOGS LIKE '{managed_catalog}'").count() > 0:
        user_catalog = managed_catalog
        user_schema = user_schema or "mmf"
    else:
        user_catalog = catalog

if not user_schema:
    user_schema = _identifier(user_email.split("@")[0])

source = f"{catalog}.{source_schema}"
reference = f"{catalog}.{source_schema}_reference"
out = f"{user_catalog}.{user_schema}"

print(f"Shared data (read): {source}")
print(f"Your outputs (write): {out}")
