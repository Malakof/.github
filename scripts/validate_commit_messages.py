#!/usr/bin/env python3
"""Validate Crystal commit messages in a Git revision range."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from conventions import CONVENTIONAL_COMMIT_RE

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

ZERO_SHA = "0" * 40


def git(args: list[str]) -> str:
    result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
    return result.stdout


def commit_exists(sha: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def is_ancestor(older: str, newer: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def push_revision_range(
    *,
    before: str,
    after: str,
    ref_name: str,
    default_branch: str,
) -> str | None:
    if before == ZERO_SHA:
        return None
    if not commit_exists(after):
        raise ValueError(f"Pushed commit {after} is unavailable after checkout")
    if commit_exists(before) and is_ancestor(before, after):
        return f"{before}..{after}"
    if ref_name == default_branch:
        raise ValueError(
            f"Refusing non-fast-forward validation on default branch {default_branch!r}"
        )

    default_ref = f"origin/{default_branch}"
    try:
        base = git(["merge-base", after, default_ref]).strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"Cannot resolve merge base between pushed commit {after} and {default_ref}"
        ) from exc
    if not base:
        raise ValueError(
            f"Empty merge base between pushed commit {after} and {default_ref}"
        )
    return f"{base}..{after}"


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
    range_group = parser.add_mutually_exclusive_group(required=True)
    range_group.add_argument("--rev-range")
    range_group.add_argument("--push-before")
    parser.add_argument("--push-after")
    parser.add_argument("--ref-name")
    parser.add_argument("--default-branch")
    parser.add_argument("--repo", required=True, help="<owner>/<name>")
    parser.add_argument("--scopes-file", type=Path, required=True)
    parser.add_argument("--blocking", default="true")
    args = parser.parse_args()

    rev_range = args.rev_range
    if args.push_before is not None:
        missing = [
            name
            for name, value in (
                ("--push-after", args.push_after),
                ("--ref-name", args.ref_name),
                ("--default-branch", args.default_branch),
            )
            if not value
        ]
        if missing:
            parser.error(f"required with --push-before: {', '.join(missing)}")
        try:
            rev_range = push_revision_range(
                before=args.push_before,
                after=args.push_after,
                ref_name=args.ref_name,
                default_branch=args.default_branch,
            )
        except ValueError as exc:
            print(f"::error::{exc}")
            return 1
        if rev_range is None:
            print(
                "::notice::Skipping pushed commit validation for new branch creation; "
                "PR validation checks base..HEAD."
            )
            return 0

    if rev_range is None:
        parser.error("a revision range is required")

    blocking = args.blocking.lower() == "true"
    severity = "error" if blocking else "warning"
    allowed = allowed_scopes(args.scopes_file, args.repo)
    issues: list[str] = []
    checked = 0

    for sha, subject, body in commits(rev_range):
        if is_merge_commit(sha, subject):
            continue
        checked += 1
        match = CONVENTIONAL_COMMIT_RE.match(subject)
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
