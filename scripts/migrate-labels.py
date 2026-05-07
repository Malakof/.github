#!/usr/bin/env python3
"""Apply governance/migration-map.yaml to one or all Crystal repos.

For each migration:
  1. List issues/PRs carrying the legacy label
  2. Add the canonical replacement label
  3. Remove the legacy label from the issue/PR
  4. Once all issues are clean, delete the legacy label from the repo

Usage:
    python scripts/migrate-labels.py --repo <owner>/<name>
    python scripts/migrate-labels.py --repo <owner>/<name> --dry-run
    python scripts/migrate-labels.py --all-crystal-repos --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def applies_to_match(applies: Any, repo_short: str) -> bool:
    if applies == "all":
        return True
    if isinstance(applies, str):
        applies = [applies]
    return repo_short in applies


def issues_with_label(repo: str, label: str) -> list[dict[str, Any]]:
    return (
        gh_json([
            "issue", "list",
            "--repo", repo,
            "--label", label,
            "--state", "all",
            "--json", "number,labels",
            "--limit", "500",
        ])
        or []
    )


def _retry_gh(cmd: list[str], attempts: int = 3) -> tuple[int, str]:
    """Run a gh command with simple retry on transient 5xx errors."""
    import time
    last_stderr = ""
    for attempt in range(attempts):
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return 0, ""
        last_stderr = result.stderr.strip()
        if "504" in last_stderr or "502" in last_stderr or "Timeout" in last_stderr:
            time.sleep(1.5 * (attempt + 1))
            continue
        return result.returncode, last_stderr
    return 1, last_stderr


def add_label(repo: str, number: int, label: str, dry_run: bool) -> str:
    if dry_run:
        return "dry-run"
    code, err = _retry_gh(
        ["gh", "issue", "edit", str(number), "--repo", repo, "--add-label", label]
    )
    return "ok" if code == 0 else f"add-failed:{err.splitlines()[0][:80] if err else ''}"


def remove_label(repo: str, number: int, label: str, dry_run: bool) -> str:
    if dry_run:
        return "dry-run"
    code, err = _retry_gh(
        ["gh", "issue", "edit", str(number), "--repo", repo, "--remove-label", label]
    )
    return "ok" if code == 0 else f"remove-failed:{err.splitlines()[0][:80] if err else ''}"


def delete_label(repo: str, label: str, dry_run: bool) -> str:
    if dry_run:
        return "dry-run"
    code, err = _retry_gh(
        ["gh", "api", "--method", "DELETE", f"repos/{repo}/labels/{label}"]
    )
    return "ok" if code == 0 else f"delete-failed:{err.splitlines()[0][:80] if err else ''}"


def migrate_repo(repo: str, migrations: list[dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    repo_short = repo.split("/")[-1]
    actions: list[dict[str, Any]] = []
    for migration in migrations:
        applies = migration.get("applies_to", "all")
        if not applies_to_match(applies, repo_short):
            continue
        from_label = migration["from"]
        to_label = migration["to"]
        items = issues_with_label(repo, from_label)
        for item in items:
            current_labels = {label["name"] for label in item.get("labels", [])}
            actions.append({
                "repo": repo,
                "issue": item["number"],
                "from": from_label,
                "to": to_label,
                "to_already_present": to_label in current_labels,
            })
            add_status = "skipped"
            if to_label not in current_labels:
                add_status = add_label(repo, item["number"], to_label, dry_run)
            remove_status = remove_label(repo, item["number"], from_label, dry_run)
            actions[-1]["add_status"] = add_status
            actions[-1]["remove_status"] = remove_status
        if items:
            actions.append({"repo": repo, "delete_label": from_label, "delete_status": delete_label(repo, from_label, dry_run)})
    return {"repo": repo, "actions": actions}


CRYSTAL_REPOS = [
    "Malakof/crystal-dark-factory-poc",
    "Malakof/crystal-dark-factory-target-lab",
    "Malakof/crystal-discord-bot",
    "Malakof/crystal-specs",
    "Malakof/crystal-assistant-ui-poc",
    "Malakof/crystal-company",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="<owner>/<name>. Mutually exclusive with --all-crystal-repos.")
    parser.add_argument("--all-crystal-repos", action="store_true")
    parser.add_argument("--migrations-file", default="governance/migration-map.yaml", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.repo and not args.all_crystal_repos:
        parser.error("Provide --repo or --all-crystal-repos.")

    data = yaml.safe_load(args.migrations_file.read_text(encoding="utf-8"))
    migrations = data.get("migrations", [])

    targets = [args.repo] if args.repo else CRYSTAL_REPOS
    summary = [migrate_repo(repo, migrations, args.dry_run) for repo in targets]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
