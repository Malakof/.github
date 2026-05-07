#!/usr/bin/env python3
"""Onboard a Crystal repo to Malakof/.github governance.

Adds:
- .crystal-governance.yaml pinning the latest stable governance version
- .github/workflows/governance-check.yml calling the reusable workflow
- .github/workflows/enforce-conventions.yml calling the reusable workflow

Opens a PR titled `chore: onboard to Crystal governance v<X.Y.Z>` on the
target repo.

Usage:
    python scripts/onboard-crystal-repo.py --repo Malakof/<name> --version v1.1.0
    python scripts/onboard-crystal-repo.py --all-crystal-repos --version v1.1.0 [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CRYSTAL_REPOS = [
    "Malakof/crystal-dark-factory-poc",
    "Malakof/crystal-dark-factory-target-lab",
    "Malakof/crystal-discord-bot",
    "Malakof/crystal-specs",
    "Malakof/crystal-assistant-ui-poc",
    "Malakof/crystal-company",
]

PIN_TEMPLATE = """schema: crystal-governance-pin/v1
governance_version: {version}
source: Malakof/.github
"""

GOVERNANCE_CHECK_TEMPLATE = """name: governance-check
on: [push, pull_request]
jobs:
  check:
    uses: Malakof/.github/.github/workflows/governance-check.yml@{version}
    with:
      strict: false
"""

ENFORCE_CONVENTIONS_TEMPLATE = """name: enforce-conventions
on: [pull_request]
jobs:
  enforce:
    uses: Malakof/.github/.github/workflows/enforce-conventions.yml@{version}
    with:
      blocking: false
"""


def gh(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["gh"] + args, capture_output=True, text=True, **kwargs)


def file_exists(repo: str, path: str) -> bool:
    result = gh(["api", f"repos/{repo}/contents/{path}", "--silent"], check=False)
    return result.returncode == 0


def onboard_repo(repo: str, version: str, dry_run: bool) -> dict:
    branch = f"chore/onboard-governance-{version}"
    pin_exists = file_exists(repo, ".crystal-governance.yaml")
    check_exists = file_exists(repo, ".github/workflows/governance-check.yml")
    enforce_exists = file_exists(repo, ".github/workflows/enforce-conventions.yml")
    skipped = pin_exists and check_exists and enforce_exists
    if skipped:
        return {"repo": repo, "action": "already-onboarded"}
    if dry_run:
        return {
            "repo": repo,
            "action": "would-onboard",
            "branch": branch,
            "needs": {
                "pin": not pin_exists,
                "check": not check_exists,
                "enforce": not enforce_exists,
            },
        }
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp) / "repo"
        clone = subprocess.run(
            ["gh", "repo", "clone", repo, str(cwd), "--", "--depth=1"],
            capture_output=True, text=True, check=False,
        )
        if clone.returncode != 0:
            return {"repo": repo, "action": "clone-failed", "stderr": clone.stderr.strip()[:200]}

        env = os.environ.copy()
        run = lambda args: subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, env=env)
        run(["git", "checkout", "-b", branch])

        if not pin_exists:
            (cwd / ".crystal-governance.yaml").write_text(PIN_TEMPLATE.format(version=version), encoding="utf-8")
        if not check_exists:
            wf = cwd / ".github" / "workflows"
            wf.mkdir(parents=True, exist_ok=True)
            (wf / "governance-check.yml").write_text(GOVERNANCE_CHECK_TEMPLATE.format(version=version), encoding="utf-8")
        if not enforce_exists:
            wf = cwd / ".github" / "workflows"
            wf.mkdir(parents=True, exist_ok=True)
            (wf / "enforce-conventions.yml").write_text(ENFORCE_CONVENTIONS_TEMPLATE.format(version=version), encoding="utf-8")

        run(["git", "add", "-A"])
        run(["git", "commit", "-m", f"chore: onboard to Crystal governance {version}"])
        push = run(["git", "push", "-u", "origin", branch])
        if push.returncode != 0:
            return {"repo": repo, "action": "push-failed", "stderr": push.stderr.strip()[:200]}

        body = f"""## Summary

Onboard this repo to the Crystal GitHub governance contract pinned at `{version}`.

## What this PR adds

- `.crystal-governance.yaml`: pin file declaring the governance version and source.
- `.github/workflows/governance-check.yml`: reusable workflow checking pin alignment + label drift on every push and PR.
- `.github/workflows/enforce-conventions.yml`: reusable workflow validating PR title (Conventional Commits) and required labels (`priority:p*`, `type:*`).

Both workflows are non-blocking by default (warnings only) until the team is comfortable. Switch `strict: true` / `blocking: true` later when ready.

## Effect

- Inheritance: this repo already inherits issue templates and PR template from `Malakof/.github`. This PR formalises the contract via the pin file.
- Labels: canonical labels were applied in batch (v1.0.x). This PR adds the CI to detect future drift.
- No code change.

## References

- Governance source: https://github.com/Malakof/.github
- Canonical doc: https://github.com/Malakof/.github/blob/main/governance/README.md
- Project v2: https://github.com/users/Malakof/projects/1
"""
        pr_create = subprocess.run(
            ["gh", "pr", "create", "--repo", repo,
             "--title", f"chore: onboard to Crystal governance {version}",
             "--body", body],
            cwd=cwd, capture_output=True, text=True, check=False,
        )
        if pr_create.returncode != 0:
            return {"repo": repo, "action": "pr-create-failed", "stderr": pr_create.stderr.strip()[:200]}
        url = pr_create.stdout.strip().splitlines()[-1]
        return {"repo": repo, "action": "onboarded", "branch": branch, "pr": url}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="<owner>/<name>")
    parser.add_argument("--all-crystal-repos", action="store_true")
    parser.add_argument("--version", required=True, help="Governance version to pin (e.g. v1.1.0)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.repo and not args.all_crystal_repos:
        parser.error("Provide --repo or --all-crystal-repos.")

    targets = [args.repo] if args.repo else CRYSTAL_REPOS
    summary = [onboard_repo(repo, args.version, args.dry_run) for repo in targets]
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
