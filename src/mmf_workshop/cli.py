"""Build and deploy MMF workshop notebooks as a Databricks DBC archive."""

from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
NOTEBOOK_DIRS = ["setup", "labs"]
NOTEBOOK_HEADER = "# Databricks notebook source"
DIST_DIR = REPO_ROOT / "dist"
# Learners only get labs/. The admin archive (Vocareum workspace_setup /
# user_setup) also carries labs/, because workspace_setup runs the Lab 4
# reference solution through ../labs/04-execute/run_cpu.
# name -> (directories, root that archive paths are relative to)
ARCHIVES = {
    "mmf-workshop-labs.dbc": (["labs"], REPO_ROOT / "labs"),
    "mmf-workshop-setup.dbc": (["setup", "labs"], REPO_ROOT),
}


def find_notebooks(dirs: list[str] = NOTEBOOK_DIRS) -> list[Path]:
    notebooks = []
    for d in dirs:
        src = REPO_ROOT / d
        if not src.exists():
            print(f"WARNING: {src} not found, skipping", file=sys.stderr)
            continue
        for py in sorted(src.rglob("*.py")):
            notebooks.append(py)
    return notebooks


def validate_notebook(path: Path) -> bool:
    first_line = path.read_text().split("\n", 1)[0].strip()
    return first_line == NOTEBOOK_HEADER


def cmd_build(args: argparse.Namespace) -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for name, (dirs, root) in ARCHIVES.items():
        rc = build_archive(dirs, root, DIST_DIR / name)
        if rc:
            return rc
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
    # (e.g. ../_includes/config) resolve after import.
    with zipfile.ZipFile(dbc_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for nb in valid:
            arcname = str(nb.relative_to(root))
            zf.write(nb, arcname)
            print(f"  + {arcname}")

    print(f"Built {dbc_path} ({len(valid)} notebooks, {dbc_path.stat().st_size} bytes)\n")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    target = f"/Users/{args.email}/mmf-workshop"

    print(f"Importing notebooks -> {target}")
    for nb in find_notebooks():
        rel = nb.relative_to(REPO_ROOT)
        ws_path = f"{target}/{rel}".removesuffix(".py")
        cmd = [
            "databricks", "workspace", "import",
            ws_path,
            "--file", str(nb),
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

    sub.add_parser("build", help="Package labs/ and setup/ into dist/mmf-workshop-{labs,setup}.dbc")

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
