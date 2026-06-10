#!/usr/bin/env python3
"""Sync canonical Crystal labels onto a target GitHub repo.

Reads governance/labels.yaml and ensures each label exists on the target
repo with the correct color and description. Idempotent. Optionally
deletes labels that are no longer in the canonical table (--prune).

Usage:
    python scripts/sync-labels.py --repo <owner>/<name>
    python scripts/sync-labels.py --repo <owner>/<name> --check-only
    python scripts/sync-labels.py --repo <owner>/<name> --check-only --allow-extra-labels
    python scripts/sync-labels.py --repo <owner>/<name> --include-dark-factory-labels
    python scripts/sync-labels.py --repo <owner>/<name> --prune
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


def fetch_existing_labels(repo: str) -> dict[str, dict[str, str]]:
    payload = gh_json(["api", f"repos/{repo}/labels", "--paginate"]) or []
    return {item["name"]: item for item in payload}


def labels_for_repo(labels_file: Path, repo: str, include_dark_factory_labels: bool = False) -> list[dict[str, str]]:
    data = yaml.safe_load(labels_file.read_text(encoding="utf-8"))
    repo_short = repo.split("/")[-1]
    out: list[dict[str, str]] = []
    for category in data.get("categories", {}).values():
        if category.get("dark_factory_context") and not include_dark_factory_labels:
            continue
        applies = category.get("applies_to", "all")
        if not applies_to_match(applies, repo_short):
            continue
        for label in category.get("labels", []):
            out.append(
                {
                    "name": label["name"],
                    "color": label["color"],
                    "description": label.get("description", ""),
                }
            )
    return out


def applies_to_match(applies: Any, repo_short: str) -> bool:
    if applies == "all":
        return True
    if isinstance(applies, str):
        applies = [applies]
    for entry in applies:
        if entry == repo_short:
            return True
        if entry.endswith("*") and repo_short.startswith(entry[:-1]):
            return True
    return False


def upsert_label(repo: str, label: dict[str, str], dry_run: bool, existing: dict[str, dict[str, str]]) -> str:
    name = label["name"]
    if name in existing:
        current = existing[name]
        same = current.get("color") == label["color"] and (current.get("description") or "") == label["description"]
        if same:
            return "ok"
        if dry_run:
            return "would-update"
        result = subprocess.run(
            [
                "gh", "api", "--method", "PATCH",
                f"repos/{repo}/labels/{name}",
                "-f", f"new_name={name}",
                "-f", f"color={label['color']}",
                "-f", f"description={label['description']}",
            ],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            stderr_first = result.stderr.strip().splitlines()[0] if result.stderr.strip() else ""
            return f"update-failed:{stderr_first[:80]}"
        return "updated"
    if dry_run:
        return "would-create"
    result = subprocess.run(
        [
            "gh", "api", "--method", "POST",
            f"repos/{repo}/labels",
            "-f", f"name={name}",
            "-f", f"color={label['color']}",
            "-f", f"description={label['description']}",
        ],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        if "Validation Failed" in result.stderr or "already_exists" in result.stderr:
            return "exists-on-server"
        stderr_first = result.stderr.strip().splitlines()[0] if result.stderr.strip() else ""
        return f"create-failed:{stderr_first[:80]}"
    return "created"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="<owner>/<name>")
    parser.add_argument("--labels-file", default="governance/labels.yaml", type=Path)
    parser.add_argument("--check-only", action="store_true", help="Report drift, do not modify.")
    parser.add_argument("--strict", default="false", help="In check-only, exit 1 on drift.")
    parser.add_argument(
        "--allow-extra-labels",
        action="store_true",
        help="In check-only strict mode, tolerate existing labels outside the canonical table.",
    )
    parser.add_argument(
        "--include-dark-factory-labels",
        action="store_true",
        help="Also sync optional Dark Factory labels; use only for a Dark Factory run/repo context.",
    )
    parser.add_argument("--prune", action="store_true", help="Delete labels not in the canonical table.")
    args = parser.parse_args()

    canonical = labels_for_repo(args.labels_file, args.repo, args.include_dark_factory_labels)
    existing = fetch_existing_labels(args.repo)
    drift = []

    for label in canonical:
        result = upsert_label(args.repo, label, args.check_only, existing)
        if result.startswith("would-") or result in {"updated", "created"}:
            drift.append((label["name"], result))

    extra: list[str] = []
    if args.prune or args.check_only:
        canonical_names = {label["name"] for label in canonical}
        for existing_name in existing:
            if existing_name not in canonical_names:
                extra.append(existing_name)
                if args.prune and not args.check_only:
                    subprocess.run(
                        ["gh", "api", "--method", "DELETE", f"repos/{args.repo}/labels/{existing_name}"],
                        check=True,
                    )

    blocking_extra = extra and not args.allow_extra_labels

    print(json.dumps({
        "repo": args.repo,
        "include_dark_factory_labels": args.include_dark_factory_labels,
        "applied": [d for d in drift if not d[1].startswith("would-")],
        "would_apply": [d for d in drift if d[1].startswith("would-")],
        "extra_labels": extra,
        "extra_labels_tolerated": bool(extra and args.allow_extra_labels),
        "ok": not drift and not blocking_extra,
    }, indent=2))

    if args.check_only and args.strict.lower() == "true" and (drift or blocking_extra):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
