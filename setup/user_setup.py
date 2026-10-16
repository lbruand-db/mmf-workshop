# Databricks notebook source
# MAGIC %md
# MAGIC # User Setup — MMF Workshop
# MAGIC
# MAGIC Runs **once per learner, as an admin**. On Vocareum this is the `user_setup`
# MAGIC entry of the course `.cfg` (called with `host` / `token` / `username`).
# MAGIC For an instructor-led workshop, pass a comma-separated list of emails in
# MAGIC `username` to install for every participant at once.
# MAGIC
# MAGIC Installs the MMF skill for Genie Code into the learner's home folder, from
# MAGIC the bundle staged by `workspace_setup` (shared installer:
# MAGIC `labs/Source/en_us/notebooks/Includes/_skill`). Lessons also install it for the
# MAGIC learner on their first Classroom setup, so this is only needed where you want it
# MAGIC in place beforehand (instructor-led workshops) or to force a reinstall:
# MAGIC
# MAGIC ```
# MAGIC /Users/{username}/
# MAGIC ├── .assistant_instructions.md      # templated with workspace URL + email
# MAGIC └── .assistant/skills/              # contents of the MMF skill bundle
# MAGIC ```
# MAGIC
# MAGIC Genie Code is path-sensitive: the leading dots matter. Safe to re-run.

# COMMAND ----------

# MAGIC %run ../labs/Source/en_us/notebooks/Includes/_skill

# COMMAND ----------

dbutils.widgets.text("host", "")
dbutils.widgets.text("token", "")
dbutils.widgets.text("username", "")
dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("schema", "m5")

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
host = dbutils.widgets.get("host") or ctx.apiUrl().get()
token = dbutils.widgets.get("token") or ctx.apiToken().get()
usernames = [u.strip() for u in dbutils.widgets.get("username").split(",") if u.strip()]
assert usernames, "username is required"

skills_dir = f"/Volumes/{dbutils.widgets.get('catalog')}/{dbutils.widgets.get('schema')}/assets/skills"

# COMMAND ----------

results = {}
for email in usernames:
    results[email] = install_mmf_skill(email, skills_dir, host, token, force=True)
    print(f"  {email}: {results[email]}")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({"status": "SUCCESS", "users": results}))
