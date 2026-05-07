#!/usr/bin/env python3
"""Configure custom autolinks for Crystal mission codes on each Crystal repo.

For each Crystal repo, creates 6 autolinks (one per REPO_PREFIX) so that
mentions like `PAUI-FEAT-001` in any issue/PR/comment become clickable links
to a search in the repo where the mission lives.

Usage:
    python scripts/setup-autolinks.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

CRYSTAL_REPOS = [
    "Malakof/crystal-dark-factory-poc",
    "Malakof/crystal-dark-factory-target-lab",
    "Malakof/crystal-discord-bot",
    "Malakof/crystal-specs",
    "Malakof/crystal-assistant-ui-poc",
    "Malakof/crystal-company",
    "Malakof/.github",
]

# REPO_PREFIX -> (mission-bearing repo, search URL)
PREFIX_TO_REPO: dict[str, str] = {
    "PAUI-": "Malakof/crystal-assistant-ui-poc",
    "DFP-": "Malakof/crystal-dark-factory-poc",
    "DFL-": "Malakof/crystal-dark-factory-target-lab",
    "BEACON-": "Malakof/crystal-discord-bot",
    "SPEC-": "Malakof/crystal-specs",
    "COMP-": "Malakof/crystal-company",
}


def gh_json(args: list[str]) -> object:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"_error": result.stderr.strip(), "_stdout": result.stdout.strip()}
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_raw": result.stdout}


def list_existing_autolinks(repo: str) -> list[dict]:
    payload = gh_json(["api", f"repos/{repo}/autolinks"])
    if not isinstance(payload, list):
        return []
    return payload


def url_template_for(prefix: str) -> str:
    target_repo = PREFIX_TO_REPO[prefix]
    return f"https://github.com/{target_repo}/issues?q=is%3Aissue+{prefix}<num>"


def create_autolink(repo: str, prefix: str, dry_run: bool) -> dict:
    url_template = url_template_for(prefix)
    if dry_run:
        return {"action": "would-create", "repo": repo, "prefix": prefix, "url": url_template}
    result = subprocess.run(
        [
            "gh", "api", "--method", "POST",
            f"repos/{repo}/autolinks",
            "-f", f"key_prefix={prefix}",
            "-f", f"url_template={url_template}",
            "-F", "is_alphanumeric=true",
        ],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return {"action": "error", "repo": repo, "prefix": prefix, "stderr": result.stderr.strip()[:200]}
    return {"action": "created", "repo": repo, "prefix": prefix}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repos", nargs="*", default=CRYSTAL_REPOS)
    args = parser.parse_args()

    summary = []
    for repo in args.repos:
        existing = list_existing_autolinks(repo)
        existing_prefixes = {item.get("key_prefix") for item in existing if isinstance(item, dict)}
        for prefix in PREFIX_TO_REPO:
            if prefix in existing_prefixes:
                summary.append({"action": "exists", "repo": repo, "prefix": prefix})
                continue
            summary.append(create_autolink(repo, prefix, args.dry_run))

    counts: dict[str, int] = {}
    for entry in summary:
        counts[entry["action"]] = counts.get(entry["action"], 0) + 1
    print(json.dumps({"counts": counts, "details": summary}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
