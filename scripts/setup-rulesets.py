#!/usr/bin/env python3
"""Apply a minimal Crystal main-branch protection ruleset to each repo.

Rules:
- restrict deletion of main
- restrict non-fast-forward (force-push) to main

Required status checks (governance-check, enforce-conventions) will be added
in v1.2.x once the onboarding PRs have been merged and the workflows have
run at least once on main.

Usage:
    python scripts/setup-rulesets.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

REPOS = [
    "Malakof/crystal-dark-factory-poc",
    "Malakof/crystal-dark-factory-target-lab",
    "Malakof/crystal-discord-bot",
    "Malakof/crystal-specs",
    "Malakof/crystal-assistant-ui-poc",
    "Malakof/crystal-company",
    "Malakof/.github",
]

RULESET_NAME = "Crystal main protection"

RULESET_PAYLOAD = {
    "name": RULESET_NAME,
    "target": "branch",
    "enforcement": "active",
    "conditions": {
        "ref_name": {
            "include": ["refs/heads/main"],
            "exclude": [],
        }
    },
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
    ],
}


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


def list_rulesets(repo: str) -> list[dict]:
    payload = gh_json(["api", f"repos/{repo}/rulesets"])
    return payload if isinstance(payload, list) else []


def find_existing_ruleset(repo: str) -> dict | None:
    for rs in list_rulesets(repo):
        if rs.get("name") == RULESET_NAME:
            return rs
    return None


def create_ruleset(repo: str, dry_run: bool) -> dict:
    if dry_run:
        return {"action": "would-create", "repo": repo, "name": RULESET_NAME}
    body = json.dumps(RULESET_PAYLOAD)
    result = subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{repo}/rulesets", "--input", "-"],
        input=body, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return {"action": "error", "repo": repo, "stderr": result.stderr.strip()[:200]}
    return {"action": "created", "repo": repo, "id": json.loads(result.stdout).get("id")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = []
    for repo in REPOS:
        existing = find_existing_ruleset(repo)
        if existing:
            summary.append({"action": "exists", "repo": repo, "id": existing.get("id")})
            continue
        summary.append(create_ruleset(repo, args.dry_run))

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
