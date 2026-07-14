#!/usr/bin/env python3
"""Validate a PR title against Conventional Commits + Crystal scopes.yaml.

Used by .github/workflows/enforce-conventions.yml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from conventions import CONVENTIONAL_TITLE_RE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--scopes-file", type=Path, required=True)
    parser.add_argument("--repo", required=True, help="<owner>/<name>")
    parser.add_argument("--blocking", default="true")
    args = parser.parse_args()

    blocking = args.blocking.lower() == "true"
    title = args.title.strip()

    match = CONVENTIONAL_TITLE_RE.match(title)
    if not match:
        msg = (
            f"Title '{title}' does not match Conventional Commits "
            "(<type>(<scope>)?: <subject>). See "
            "https://github.com/Malakof/.github/blob/main/governance/README.md#12-conventional-commits"
        )
        print(f"::{'error' if blocking else 'warning'}::{msg}")
        return 1 if blocking else 0

    scope = match.group("scope")
    subject = match.group("subject")

    if len(subject) > 72:
        print(f"::warning::Subject is {len(subject)} chars, recommended ≤ 72.")

    if subject.endswith("."):
        print("::warning::Subject should not end with a period.")

    if scope:
        data = yaml.safe_load(args.scopes_file.read_text(encoding="utf-8"))
        repo_short = args.repo.split("/")[-1]
        repo_key = args.repo if args.repo in data.get("scopes", {}) else repo_short
        allowed = set(data.get("scopes", {}).get(repo_key, [])) | set(data.get("universal_scopes", []))
        if allowed and scope not in allowed:
            msg = (
                f"Scope '{scope}' not in scopes.yaml for {args.repo}. "
                f"Allowed: {sorted(allowed)}"
            )
            print(f"::{'error' if blocking else 'warning'}::{msg}")
            return 1 if blocking else 0

    print(f"::notice::Title OK — type={match.group('type')} scope={scope or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
