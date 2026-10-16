# Databricks notebook source
# MAGIC %md
# MAGIC # Checkpoint helpers
# MAGIC
# MAGIC Included by every lab `checkpoint.py` via `%run ../_includes/checks`.
# MAGIC `finish()` prints a PASS/FAIL report and exits with JSON that
# MAGIC `setup/autograde` turns into a Vocareum grade:
# MAGIC
# MAGIC ```json
# MAGIC {"lab": "Lab 1", "status": "FAIL", "checks": [{"name": "...", "ok": false, "detail": "..."}]}
# MAGIC ```

# COMMAND ----------

import json


def finish(lab: str, checks: list[tuple[str, bool, str]]) -> None:
    all_pass = all(ok for _, ok, _ in checks)
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
    print(f"\n{lab}: {'PASS' if all_pass else 'FAIL'}")
    dbutils.notebook.exit(json.dumps({
        "lab": lab,
        "status": "PASS" if all_pass else "FAIL",
        "checks": [{"name": n, "ok": bool(ok), "detail": d} for n, ok, d in checks],
    }))
