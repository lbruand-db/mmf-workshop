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
# MAGIC the bundle staged by `workspace_setup`:
# MAGIC
# MAGIC ```
# MAGIC /Users/{username}/
# MAGIC ├── .assistant_instructions.md      # templated with workspace URL + email
# MAGIC └── .assistant/skills/              # contents of the MMF skill bundle
# MAGIC ```
# MAGIC
# MAGIC Genie Code is path-sensitive: the leading dots matter. Safe to re-run.

# COMMAND ----------

dbutils.widgets.text("host", "")
dbutils.widgets.text("token", "")
dbutils.widgets.text("username", "")
dbutils.widgets.text("catalog", "mmf")
dbutils.widgets.text("schema", "m5")

host = dbutils.widgets.get("host") or spark.conf.get("spark.databricks.workspaceUrl")
host = "https://" + host.removeprefix("https://").removeprefix("http://").rstrip("/")
token = (
    dbutils.widgets.get("token")
    or dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
)
usernames = [u.strip() for u in dbutils.widgets.get("username").split(",") if u.strip()]
assert usernames, "username is required"

skills_dir = f"/Volumes/{dbutils.widgets.get('catalog')}/{dbutils.widgets.get('schema')}/assets/skills"

# COMMAND ----------

import base64
import re
from pathlib import Path

import requests

session = requests.Session()
session.headers["Authorization"] = f"Bearer {token}"


def api(method: str, path: str, **payload):
    resp = session.request(method, f"{host}/api/2.0/{path}", json=payload)
    resp.raise_for_status()
    return resp.json()


def import_file(local: Path, ws_path: str, content: bytes | None = None):
    data = content if content is not None else local.read_bytes()
    api("POST", "workspace/import", path=ws_path, format="AUTO", overwrite=True,
        content=base64.b64encode(data).decode())


bundle = sorted(p for p in Path(skills_dir, "bundle").iterdir() if p.is_file())
instructions = Path(skills_dir, "assistant_instructions.md").read_text()
print(f"Skill bundle: {len(bundle)} files from {skills_dir} "
      f"(ref {Path(skills_dir, 'VERSION').read_text()[:12]})")

# COMMAND ----------

def personalise(text: str, email: str) -> str:
    """Fill the `### User Context` placeholders with this learner's details."""
    text = re.sub(r"^- Workspace: .*$", f"- Workspace: {host}", text, count=1, flags=re.M)
    return re.sub(r"^- Email: .*$", f"- Email: {email}", text, count=1, flags=re.M)


for email in usernames:
    home = f"/Users/{email}"
    api("POST", "workspace/mkdirs", path=f"{home}/.assistant/skills")
    for f in bundle:
        import_file(f, f"{home}/.assistant/skills/{f.name}")
    import_file(None, f"{home}/.assistant_instructions.md",
                content=personalise(instructions, email).encode())
    print(f"  OK  {email}: {len(bundle)} skill files + .assistant_instructions.md")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({"status": "SUCCESS", "users": usernames, "skill_files": len(bundle)}))
