"""Build and deploy MMF workshop notebooks as source-format notebook archives (.zip)."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from functools import cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
NOTEBOOK_DIRS = ["setup", "labs"]
NOTEBOOK_HEADER = "# Databricks notebook source"
DIST_DIR = REPO_ROOT / "dist"
# Copyrighted third-party reference material, kept locally for structure only.
# It must never be committed or packaged (see SPECS/RESTRUCTURE.md).
REFERENCE_DIR = ".sources"
COURSE_NOTEBOOKS = "labs/Source/en_us/notebooks"
# Learners only get the course notebooks. The admin archive (Vocareum
# workspace_setup / user_setup) also carries them, because workspace_setup runs
# the reference solution (lesson 3.2) through ../labs/Source/en_us/notebooks/...
# labs/Source/en_us/instructor/ is never packaged.
# name -> (directories, root that archive paths are relative to)
ARCHIVES = {
    "mmf-workshop-labs.zip": ([COURSE_NOTEBOOKS], REPO_ROOT / COURSE_NOTEBOOKS),
    "mmf-workshop-setup.zip": (["setup", COURSE_NOTEBOOKS], REPO_ROOT),
}


COURSE_NAME = "Many-Model Forecasting with Genie Code"
REPO_URL = "https://github.com/lbruand-db/mmf-workshop"
# Changes here make a build "dirty": the packaged content no longer matches the commit.
PACKAGED_PATHS = ["setup", "labs", "src", "pyproject.toml"]


def project_version() -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', (REPO_ROOT / "pyproject.toml").read_text(), re.M)
    return match.group(1) if match else "unknown"


def _git(*args: str) -> str | None:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


@cache
def build_info() -> dict:
    """Identifies a build: project version + git commit, so a deployed course can be
    traced back to its source. `build_id` is `<version>+g<short commit>[.dirty]`."""
    version = project_version()
    commit = _git("rev-parse", "HEAD") or "unknown"
    dirty = bool(_git("status", "--porcelain", "--", *PACKAGED_PATHS))
    pushed = bool(_git("branch", "-r", "--contains", "HEAD")) if commit != "unknown" else False
    short = commit[:7]
    return {
        "course_name": COURSE_NAME,
        "version": version,
        "build_id": f"{version}+g{short}" + (".dirty" if dirty else ""),
        "commit": commit,
        "commit_url": f"{REPO_URL}/commit/{commit}",
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "dirty": dirty,
        "pushed": pushed,
        "built_on": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render(nb: Path) -> str:
    """Notebook source as packaged: fills the {{...}} build placeholders
    (Version Info, Includes/_common, setup/workspace_setup)."""
    text = nb.read_text()
    if "{{" not in text:
        return text
    info = build_info()
    values = {
        "course_name": info["course_name"],
        "version_number": info["version"],
        "build_id": info["build_id"],
        "commit": info["commit"],
        "commit_url": info["commit_url"],
        "built_on": info["built_on"],
        "dirty_note": (
            "**Built from uncommitted changes** — this build does not match any commit exactly."
            if info["dirty"] else "Built from a clean checkout of the commit above."
        ),
    }
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def find_notebooks(dirs: list[str] = NOTEBOOK_DIRS) -> list[Path]:
    notebooks = []
    for d in dirs:
        src = REPO_ROOT / d
        if not src.exists():
            print(f"WARNING: {src} not found, skipping", file=sys.stderr)
            continue
        for py in sorted(src.rglob("*.py")):
            if REFERENCE_DIR in py.relative_to(REPO_ROOT).parts:
                continue
            notebooks.append(py)
    return notebooks


def validate_notebook(path: Path) -> bool:
    first_line = path.read_text().split("\n", 1)[0].strip()
    return first_line == NOTEBOOK_HEADER


def check_reference_material() -> int:
    """Fail if any reference material is tracked by git."""
    tracked = subprocess.run(
        ["git", "ls-files", "--", REFERENCE_DIR],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    if tracked:
        print(f"ERROR: {REFERENCE_DIR}/ is reference material and must not be committed:", file=sys.stderr)
        for t in tracked:
            print(f"  {t}", file=sys.stderr)
        print(f"Run: git rm -r --cached {REFERENCE_DIR}", file=sys.stderr)
        return 1
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    rc = check_reference_material()
    if rc:
        return rc
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    info = build_info()
    for name, (dirs, root) in ARCHIVES.items():
        rc = build_archive(dirs, root, DIST_DIR / name)
        if rc:
            return rc
    (DIST_DIR / "BUILD_INFO.json").write_text(json.dumps(
        {**info, "archives": sorted(ARCHIVES)}, indent=2) + "\n")
    print(f"Build {info['build_id']} (commit {info['commit']}) -> {DIST_DIR / 'BUILD_INFO.json'}")
    if info["dirty"]:
        print("WARNING: uncommitted changes in " + ", ".join(PACKAGED_PATHS)
              + " — commit them before deploying, so the build can be traced.", file=sys.stderr)
    elif not info["pushed"]:
        print("WARNING: commit not pushed — push it, so the commit link in Version Info resolves.", file=sys.stderr)
    return 0


def build_archive(dirs: list[str], root: Path, dbc_path: Path) -> int:
    notebooks = find_notebooks(dirs)
    if not notebooks:
        print(f"ERROR: no notebooks found in {dirs}", file=sys.stderr)
        return 1

    valid, invalid = [], []
    for nb in notebooks:
        if validate_notebook(nb):
            valid.append(nb)
        else:
            invalid.append(nb)

    if invalid:
        print("WARNING: skipping non-notebook files:", file=sys.stderr)
        for p in invalid:
            print(f"  {p.relative_to(REPO_ROOT)}", file=sys.stderr)

    if not valid:
        print(f"ERROR: no valid Databricks notebooks found in {dirs}", file=sys.stderr)
        return 1

    # Paths are relative to `root` so relative %run / notebook.run references
    # (e.g. ../Includes/_common) resolve after import.
    with zipfile.ZipFile(dbc_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for nb in valid:
            arcname = str(nb.relative_to(root))
            zf.writestr(arcname, render(nb))
            print(f"  + {arcname}")

    print(f"Built {dbc_path} ({len(valid)} notebooks, {dbc_path.stat().st_size} bytes)\n")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    target = f"/Users/{args.email}/mmf-workshop"

    print(f"Importing notebooks -> {target} (build {build_info()['build_id']})")
    tmp = Path(tempfile.mkdtemp())
    for nb in find_notebooks():
        rel = nb.relative_to(REPO_ROOT)
        ws_path = f"{target}/{rel}".removesuffix(".py")
        rendered = tmp / nb.name
        rendered.write_text(render(nb))
        cmd = [
            "databricks", "workspace", "import",
            ws_path,
            "--file", str(rendered),
            "--format", "SOURCE",
            "--language", "PYTHON",
            "--overwrite",
        ]
        if args.profile:
            cmd.extend(["--profile", args.profile])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAIL {rel}: {result.stderr.strip()}", file=sys.stderr)
            return result.returncode
        print(f"  + {rel}")

    print(f"Deployed {len(find_notebooks())} notebooks to {target}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mmf-workshop",
        description="Build and deploy MMF workshop notebooks",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="Package the course notebooks and setup/ into dist/mmf-workshop-{labs,setup}.zip")

    install_p = sub.add_parser("install", help="Import notebook sources into a Databricks workspace")
    install_p.add_argument("--email", required=True, help="Target user email")
    install_p.add_argument("--profile", default=None, help="Databricks CLI profile")

    args = parser.parse_args()

    if args.command == "build":
        sys.exit(cmd_build(args))
    elif args.command == "install":
        sys.exit(cmd_install(args))


if __name__ == "__main__":
    main()
