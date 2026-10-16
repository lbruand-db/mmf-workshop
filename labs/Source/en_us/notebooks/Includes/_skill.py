# Databricks notebook source
# MAGIC %md
# MAGIC # MMF skill installer
# MAGIC
# MAGIC Defines `install_mmf_skill()`. Used by:
# MAGIC - every lesson's Classroom setup (via `_common`): learners install the skill into
# MAGIC   their **own** home folder — no admin or per-user platform hook needed;
# MAGIC - `setup/user_setup`: an admin installs it for other users.
# MAGIC
# MAGIC Installs from the bundle that `setup/workspace_setup` stages in
# MAGIC `/Volumes/<catalog>/<schema>/assets/skills/`:
# MAGIC
# MAGIC ```
# MAGIC /Users/{email}/
# MAGIC ├── .assistant_instructions.md      # templated with workspace URL + email
# MAGIC └── .assistant/skills/              # contents of the MMF skill bundle, plus a version marker
# MAGIC ```
# MAGIC
# MAGIC Genie Code is path-sensitive: the leading dots matter. Re-running is cheap: it does
# MAGIC nothing when the staged version is already installed.

# COMMAND ----------

import base64
import re
from pathlib import Path

import requests

SKILL_VERSION_MARKER = ".mmf-skill-version.txt"


class _WorkspaceFiles:
    """Minimal Workspace API client (import / mkdirs / status / read)."""

    def __init__(self, host: str, token: str):
        self.host = "https://" + host.removeprefix("https://").removeprefix("http://").rstrip("/")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _call(self, method: str, path: str, **kwargs):
        resp = self.session.request(method, f"{self.host}/api/2.0/workspace/{path}", **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def exists(self, ws_path: str) -> bool:
        resp = self.session.get(f"{self.host}/api/2.0/workspace/get-status", params={"path": ws_path})
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True

    def read(self, ws_path: str) -> str | None:
        resp = self.session.get(f"{self.host}/api/2.0/workspace/export",
                                params={"path": ws_path, "format": "SOURCE"})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return base64.b64decode(resp.json().get("content", "")).decode()

    def mkdirs(self, ws_path: str) -> None:
        self._call("POST", "mkdirs", json={"path": ws_path})

    def write(self, ws_path: str, data: bytes) -> None:
        self._call("POST", "import", json={
            "path": ws_path, "format": "AUTO", "overwrite": True,
            "content": base64.b64encode(data).decode(),
        })


def _personalise(instructions: str, host: str, email: str) -> str:
    """Fill the `### User Context` placeholders with this user's details."""
    text = re.sub(r"^- Workspace: .*$", f"- Workspace: {host}", instructions, count=1, flags=re.M)
    return re.sub(r"^- Email: .*$", f"- Email: {email}", text, count=1, flags=re.M)


def install_mmf_skill(email: str, skills_dir: str, host: str, token: str,
                      force: bool = False) -> str:
    """Install the staged MMF skill for `email`; return a one-line status.

    Does nothing if the staged version is already installed, unless `force`.
    `.assistant_instructions.md` is only overwritten if it doesn't exist, if an
    earlier install of ours wrote it (recorded in the marker), or with `force` — so
    a learner's own instructions are never silently replaced.
    """
    staged = Path(skills_dir)
    if not (staged / "VERSION").exists():
        return f"not installed — no staged bundle in {skills_dir} (has setup/workspace_setup run?)"
    version = (staged / "VERSION").read_text().strip()

    ws = _WorkspaceFiles(host, token)
    home = f"/Users/{email}"
    marker = f"{home}/.assistant/skills/{SKILL_VERSION_MARKER}"
    # Marker: line 1 = installed version; line 2 = "instructions=ours" if we wrote
    # .assistant_instructions.md (so later upgrades may replace it), else "instructions=kept".
    previous = (ws.read(marker) or "").split()
    installed = previous[0] if previous else None
    ours = "instructions=ours" in previous
    if installed == version and not force:
        return f"already installed ({version[:12]})"

    ws.mkdirs(f"{home}/.assistant/skills")
    bundle = sorted(p for p in (staged / "bundle").iterdir() if p.is_file())
    for f in bundle:
        ws.write(f"{home}/.assistant/skills/{f.name}", f.read_bytes())

    instructions_path = f"{home}/.assistant_instructions.md"
    note = ""
    if force or ours or not ws.exists(instructions_path):
        instructions = (staged / "assistant_instructions.md").read_text()
        ws.write(instructions_path, _personalise(instructions, ws.host, email).encode())
        ours = True
    else:
        note = (f"; kept your existing {instructions_path} — merge the MMF instructions from "
                f"{staged / 'assistant_instructions.md'} into it if Genie Code doesn't follow the MMF workflow")

    ws.write(marker, f"{version}\ninstructions={'ours' if ours else 'kept'}\n".encode())
    return f"installed {len(bundle)} skill files ({version[:12]}){note}"
