#!/usr/bin/env python3
"""Validate Crystal commit messages in a Git revision range."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

COMMIT_RE = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?P<bang>!)?"
    r"(?:\((?P<scope>[a-z0-9._-]+)\))?"
    r": (?P<emoji>\S+) (?P<subject>.+)$"
)

ALLOWED_EMOJIS = {
    "✨",
    "🐛",
    "📝",
    "♻️",
    "✅",
    "⬆️",
    "👷",
    "🔒",
    "🚀",
    "🧹",
    "⚡",
}

MERGE_SUBJECTS = (
    "Merge ",
    "Revert \"Merge ",
)


def git(args: list[str]) -> str:
    result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
    return result.stdout


def allowed_scopes(scopes_file: Path, repo: str) -> set[str]:
    data = yaml.safe_load(scopes_file.read_text(encoding="utf-8"))
    repo_short = repo.split("/")[-1]
    repo_key = repo if repo in data.get("scopes", {}) else repo_short
    return set(data.get("scopes", {}).get(repo_key, [])) | set(data.get("universal_scopes", []))


def commits(rev_range: str) -> list[tuple[str, str, str]]:
    raw = git(["log", "--format=%H%x00%s%x00%b%x1e", rev_range])
    out: list[tuple[str, str, str]] = []
    for item in raw.strip("\x1e\n").split("\x1e"):
        if not item.strip():
            continue
        sha, subject, body = (item.split("\x00", 2) + ["", ""])[:3]
        out.append((sha, subject.strip(), body.strip()))
    return out


def is_merge_commit(sha: str, subject: str) -> bool:
    if not subject.startswith(MERGE_SUBJECTS):
        return False
    parents = git(["rev-list", "--parents", "-n", "1", sha]).strip().split()
    return len(parents) > 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rev-range", required=True)
    parser.add_argument("--repo", required=True, help="<owner>/<name>")
    parser.add_argument("--scopes-file", type=Path, required=True)
    parser.add_argument("--blocking", default="true")
    args = parser.parse_args()

    blocking = args.blocking.lower() == "true"
    severity = "error" if blocking else "warning"
    allowed = allowed_scopes(args.scopes_file, args.repo)
    issues: list[str] = []
    checked = 0

    for sha, subject, body in commits(args.rev_range):
        if is_merge_commit(sha, subject):
            continue
        checked += 1
        match = COMMIT_RE.match(subject)
        if not match:
            issues.append(
                f"{sha[:12]} subject must match '<type>(<scope>)?: <emoji> <subject>': {subject!r}"
            )
        if "Co-authored-by:" in body:
            issues.append(f"{sha[:12]} contains a forbidden Co-authored-by footer")
        if not match:
            continue

        emoji = match.group("emoji")
        if emoji not in ALLOWED_EMOJIS:
            issues.append(f"{sha[:12]} uses unsupported emoji {emoji!r} in subject: {subject!r}")

        scope = match.group("scope")
        if scope and allowed and scope not in allowed:
            issues.append(f"{sha[:12]} scope {scope!r} is not allowed for {args.repo}")

    for issue in issues:
        print(f"::{severity}::{issue}")

    if issues:
        return 1 if blocking else 0

    print(f"::notice::Commit messages OK — checked {checked} non-merge commit(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
