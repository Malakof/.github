#!/usr/bin/env python3
"""Import all open issues from Crystal repos into the Crystal Missions Project v2.

Usage:
    python scripts/import-issues-to-project.py [--state open|closed|all] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

REPOS = [
    "Malakof/crystal-dark-factory-poc",
    "Malakof/crystal-dark-factory-target-lab",
    "Malakof/crystal-discord-bot",
    "Malakof/crystal-specs",
    "Malakof/crystal-assistant-ui-poc",
    "Malakof/crystal-company",
]

PROJECT_NUMBER = 1
PROJECT_OWNER = "Malakof"


def gh_json(args: list[str]) -> object:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"_error": result.stderr.strip()[:200]}
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_raw": result.stdout[:200]}


def list_issues(repo: str, state: str) -> list[dict]:
    payload = gh_json([
        "issue", "list",
        "--repo", repo,
        "--state", state,
        "--json", "number,url,title",
        "--limit", "500",
    ]) or []
    return payload if isinstance(payload, list) else []


def add_to_project(url: str, dry_run: bool) -> str:
    if dry_run:
        return "would-add"
    for attempt in range(3):
        result = subprocess.run(
            ["gh", "project", "item-add", str(PROJECT_NUMBER),
             "--owner", PROJECT_OWNER, "--url", url],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            return "added"
        err = result.stderr.strip()
        if "already in the project" in err.lower() or "exists" in err.lower():
            return "already-in-project"
        if "504" in err or "502" in err or "Timeout" in err:
            time.sleep(1.5 * (attempt + 1))
            continue
        return f"error:{err.splitlines()[0][:80]}"
    return "max-retries"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="open", choices=["open", "closed", "all"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary: dict[str, dict[str, int]] = {}
    total_issues = 0

    for repo in REPOS:
        issues = list_issues(repo, args.state)
        repo_summary = {"total": len(issues), "added": 0, "already": 0, "error": 0, "would": 0}
        for issue in issues:
            status = add_to_project(issue["url"], args.dry_run)
            if status == "added":
                repo_summary["added"] += 1
            elif status == "already-in-project":
                repo_summary["already"] += 1
            elif status == "would-add":
                repo_summary["would"] += 1
            else:
                repo_summary["error"] += 1
                print(f"[{repo} #{issue['number']}] {status}", file=sys.stderr)
        summary[repo] = repo_summary
        total_issues += repo_summary["total"]
        print(f"  {repo}: {repo_summary}")

    print(f"\nTotal: {total_issues} issues processed across {len(REPOS)} repos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
