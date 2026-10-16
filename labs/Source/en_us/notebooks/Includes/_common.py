# Databricks notebook source
# MAGIC %md
# MAGIC # Common lesson setup
# MAGIC
# MAGIC Run by every `Classroom-Setup-x.y` notebook. Resolves where the learner
# MAGIC **reads** shared data and **writes** outputs, and defines the helpers the
# MAGIC setups use to put a lesson's prerequisites in place.
# MAGIC
# MAGIC | Variable | Meaning | Default |
# MAGIC |----------|---------|---------|
# MAGIC | `source` | Shared, read-only M5 data (`catalog`.`source_schema` widgets) | `mmf.m5` |
# MAGIC | `reference` | Shared, read-only reference results | `mmf.m5_reference` |
# MAGIC | `out` | Learner outputs (`user_catalog`.`user_schema` widgets) | see below |
# MAGIC | `user_email` | The learner | current user |
# MAGIC
# MAGIC **Output location** — the first that applies:
# MAGIC 1. The `user_catalog` / `user_schema` widgets, when set (e.g. by `setup/workspace_setup`).
# MAGIC 2. The lab platform's per-user metadata table `<catalog>.ops.meta` (keys
# MAGIC    `catalog_name`, `schema_name`, `username`), when it exists for this user.
# MAGIC 3. The Vocareum managed catalog named after the user
# MAGIC    (`vocuser12345@vocareum.com` → `vocuser12345_vocareum_com`), schema `mmf`.
# MAGIC 4. Elsewhere (instructor-led workshop): `{catalog}.{user}`, derived from the email.


# COMMAND ----------

import re

dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("source_schema", "m5")
dbutils.widgets.text("user_catalog", "")
dbutils.widgets.text("user_schema", "")

catalog = dbutils.widgets.get("catalog")
source_schema = dbutils.widgets.get("source_schema")
user_catalog = dbutils.widgets.get("user_catalog")
user_schema = dbutils.widgets.get("user_schema")

user_email = spark.sql("select current_user() as user").collect()[0]["user"]


def _identifier(s: str) -> str:
    """Lower-case and replace characters not allowed in unquoted UC names."""
    return re.sub(r"[^a-z0-9_]", "_", s.lower())


def _platform_meta() -> dict:
    """Per-user key/values the lab platform publishes in `<catalog>.ops.meta`, if any."""
    current = spark.sql("select current_catalog() as c").collect()[0]["c"]
    for meta_catalog in dict.fromkeys([current, "dbacademy"]):
        try:
            rows = spark.sql(f"SELECT key, value FROM {meta_catalog}.ops.meta").collect()
        except Exception:
            continue
        meta = {r["key"]: r["value"] for r in rows}
        # Only trust metadata that describes this user.
        if meta.get("username", user_email) == user_email:
            return meta
    return {}


resolved_by = "widgets"
if not user_catalog:
    meta = _platform_meta()
    managed_catalog = _identifier(user_email)
    if meta.get("catalog_name"):
        user_catalog, resolved_by = meta["catalog_name"], "lab platform metadata"
        user_schema = user_schema or meta.get("schema_name") or "mmf"
    elif spark.sql(f"SHOW CATALOGS LIKE '{managed_catalog}'").count() > 0:
        user_catalog, resolved_by = managed_catalog, "Vocareum managed catalog"
        user_schema = user_schema or "mmf"
    else:
        user_catalog, resolved_by = catalog, "workshop default"

if not user_schema:
    user_schema = _identifier(user_email.split("@")[0])

source = f"{catalog}.{source_schema}"
reference = f"{catalog}.{source_schema}_reference"
out = f"{user_catalog}.{user_schema}"

print(f"Shared data (read): {source}")
print(f"Your outputs (write): {out}  [{resolved_by}]")

# COMMAND ----------

def ensure_schema() -> None:
    """Create the learner's output schema. Never creates a catalog: on Vocareum,
    catalogs a learner creates are dropped when that learner's lab ends."""
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {out}")


def copy_table(src: str, name: str) -> int:
    """Overwrite `{out}.{name}` with a copy of table `src`; return its row count."""
    (
        spark.table(src)
        .write.format("delta").mode("overwrite").option("overwriteSchema", "true")
        .saveAsTable(f"{out}.{name}")
    )
    return spark.table(f"{out}.{name}").count()


def ensure_table(name: str, src: str) -> None:
    """Make sure `{out}.{name}` exists with rows, copying it from `src` if not —
    so a lesson can be started without doing the previous ones."""
    target = f"{out}.{name}"
    if spark.catalog.tableExists(target) and not spark.table(target).isEmpty():
        print(f"  OK  {target} (from your earlier work)")
    else:
        print(f"  OK  {target} <- {src} ({copy_table(src, name)} rows)")

# COMMAND ----------

# MAGIC %run ./_skill

# COMMAND ----------

skills_dir = f"/Volumes/{catalog}/{source_schema}/assets/skills"


def ensure_mmf_skill() -> None:
    """Install the MMF skill for Genie Code into the learner's own home folder,
    from the bundle staged by `setup/workspace_setup`. Never fails the lesson."""
    try:
        ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        status = install_mmf_skill(user_email, skills_dir, ctx.apiUrl().get(), ctx.apiToken().get())
        print(f"  MMF skill: {status}")
    except Exception as e:
        print(f"  WARN  MMF skill install failed: {e}")
        print("        Ask the instructor to run setup/user_setup for you.")
