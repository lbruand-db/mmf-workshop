# Databricks notebook source
# MAGIC %md
# MAGIC # Autograde — MMF Workshop
# MAGIC
# MAGIC Vocareum `autograde` entry (runs when the learner clicks **Submit**, as an
# MAGIC admin, with `host` / `token` / `username` / `table`). Runs every lab's
# MAGIC `checkpoint` for the learner and writes one row per lab to `table`:
# MAGIC
# MAGIC | Column | Value |
# MAGIC |--------|-------|
# MAGIC | `rubric` | `lab0`, `lab1`, `lab4`, `lab5` — must match the rubric names in the Vocareum part configuration |
# MAGIC | `score` | `max_score` if the checkpoint passes, else `0` |
# MAGIC | `feedback` | The failed checks, when the score is below the maximum |
# MAGIC
# MAGIC Also usable by an instructor: set `username` to a participant's email and
# MAGIC leave `table` empty to just print the grades.

# COMMAND ----------

dbutils.widgets.text("host", "")
dbutils.widgets.text("token", "")
dbutils.widgets.text("username", "")
dbutils.widgets.text("table", "")
dbutils.widgets.text("max_score", "1")

username = dbutils.widgets.get("username")
table = dbutils.widgets.get("table")
max_score = int(dbutils.widgets.get("max_score"))
assert username, "username is required"

RUBRICS = {
    "lab0": "00-setup",
    "lab1": "01-prep",
    "lab4": "04-execute",
    "lab5": "05-evaluate",
}

# COMMAND ----------

import json

rows = []
for rubric, lab_dir in RUBRICS.items():
    try:
        result = json.loads(dbutils.notebook.run(f"../labs/{lab_dir}/checkpoint", 900, {"username": username}))
        passed = result["status"] == "PASS"
        feedback = "; ".join(f"{c['name']}: {c['detail']}".strip(": ") for c in result["checks"] if not c["ok"])
    except Exception as e:
        passed, feedback = False, f"Checkpoint could not run: {e}"
    rows.append((rubric, max_score if passed else 0, feedback[:255]))
    print(f"  {rubric}: {'PASS' if passed else 'FAIL'} {feedback}")

# COMMAND ----------

if table:
    spark.sql(f"CREATE OR REPLACE TABLE {table} (rubric VARCHAR(255), score INT, feedback VARCHAR(255))")
    spark.createDataFrame(rows, "rubric STRING, score INT, feedback STRING").write.insertInto(table)
    print(f"Wrote {len(rows)} grades to {table}")

dbutils.notebook.exit(json.dumps({"username": username, "grades": rows}))
