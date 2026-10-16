# Databricks notebook source
# MAGIC %md
# MAGIC # Checkpoint helpers
# MAGIC
# MAGIC Run by the *Check your work* section of every lesson via `%run ../Includes/_checks`.
# MAGIC `finish()` prints a PASS/FAIL report for the learner and exits with JSON,
# MAGIC so a scripted smoke test can read the result:
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
