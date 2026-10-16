#!/usr/bin/env python3
"""Reap what an MMF workshop learner created outside their managed catalog.

Call from the course's Vocareum ``lab_end.py`` (End Lab Behavior must be
*terminate*, or lab_end doesn't run):

    from mmf_lab_end import reap_user
    reap_user(host, token, username)

or from a shell wrapper:

    python3 mmf_lab_end.py --host "$HOST" --token "$TOKEN" --username "$USERNAME"

Vocareum drops the learner's managed catalog (tables, UC models) on its own.
The MMF skills also create workspace objects that live outside it, which keep
costing money until removed:

- Jobs the learner created (Skill 4: one job per model class), and their runs
- One-time job runs the learner submitted
- Clusters the learner created (Skill 3 provisions CPU/GPU clusters)
- MLflow experiments in the learner's home folder

Standard library only, so it runs in the Vocareum container as-is.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request


class Client:
    def __init__(self, host: str, token: str):
        self.host = "https://" + host.removeprefix("https://").removeprefix("http://").rstrip("/")
        self.token = token

    def call(self, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
        url = f"{self.host}/api/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
        return json.loads(payload) if payload else {}

    def paginate(self, path: str, key: str, params: dict | None = None):
        params = dict(params or {})
        while True:
            page = self.call("GET", path, params=params)
            yield from page.get(key, [])
            token = page.get("next_page_token")
            if not token:
                return
            params["page_token"] = token


def reap_user(host: str, token: str, username: str) -> dict[str, int]:
    """Delete the learner's jobs, runs, clusters and experiments. Returns counts."""
    api = Client(host, token)
    counts = {"jobs": 0, "runs": 0, "clusters": 0, "experiments": 0}

    def attempt(what: str, fn, *args, **kwargs) -> bool:
        try:
            fn(*args, **kwargs)
            return True
        except Exception as e:  # keep reaping the rest
            print(f"  WARN  {what}: {e}", file=sys.stderr)
            return False

    # Active runs first (job runs and one-time submitted runs), so deletes don't race them.
    for run in api.paginate("2.2/jobs/runs/list", "runs", {"active_only": "true", "limit": 25}):
        if run.get("creator_user_name") == username:
            if attempt(f"cancel run {run['run_id']}", api.call, "POST", "2.2/jobs/runs/cancel",
                       body={"run_id": run["run_id"]}):
                counts["runs"] += 1

    for job in api.paginate("2.2/jobs/list", "jobs", {"limit": 100}):
        if job.get("creator_user_name") == username:
            if attempt(f"delete job {job['job_id']}", api.call, "POST", "2.2/jobs/delete",
                       body={"job_id": job["job_id"]}):
                counts["jobs"] += 1

    for cluster in api.call("GET", "2.0/clusters/list").get("clusters", []):
        if cluster.get("creator_user_name") == username and cluster.get("cluster_source") in ("UI", "API"):
            if attempt(f"delete cluster {cluster['cluster_id']}", api.call, "POST", "2.0/clusters/permanent-delete",
                       body={"cluster_id": cluster["cluster_id"]}):
                counts["clusters"] += 1

    home = f"/Users/{username}/"
    experiments = api.call("POST", "2.0/mlflow/experiments/search",
                           body={"filter": f"name LIKE '{home}%'", "max_results": 1000})
    for exp in experiments.get("experiments", []):
        if attempt(f"delete experiment {exp['name']}", api.call, "POST", "2.0/mlflow/experiments/delete",
                   body={"experiment_id": exp["experiment_id"]}):
            counts["experiments"] += 1

    print(f"Reaped for {username}: {counts}")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--host", required=True, help="Workspace URL")
    parser.add_argument("--token", required=True, help="Admin token")
    parser.add_argument("--username", required=True, help="Learner email")
    args = parser.parse_args()
    reap_user(args.host, args.token, args.username)


if __name__ == "__main__":
    main()
