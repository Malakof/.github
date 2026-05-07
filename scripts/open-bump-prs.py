#!/usr/bin/env python3
"""Open `chore: bump governance to vX.Y.Z` PRs across Crystal repos.

Triggered by .github/workflows/on-release-bump.yml on each new tag of
Malakof/.github. For each repo whose `.crystal-governance.yaml` pin is
older than the new tag (or missing), open a PR that updates the pin.

Usage:
    python scripts/open-bump-prs.py --new-version v1.1.0 \\
      --org Malakof --include-prefix crystal- \\
      --exclude-suffix -test,-scratch
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PIN_FILENAME = ".crystal-governance.yaml"
BRANCH_PREFIX = "chore/bump-governance-"


def gh_json(args: list[str]) -> object:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def list_target_repos(org: str, include_prefix: str, exclude_suffixes: list[str]) -> list[str]:
    payload = gh_json([
        "repo", "list", org,
        "--limit", "200",
        "--json", "name,isArchived",
    ]) or []
    out: list[str] = []
    for repo in payload:
        name = repo["name"]
        if repo.get("isArchived"):
            continue
        if not name.startswith(include_prefix):
            continue
        if any(name.endswith(suffix) for suffix in exclude_suffixes):
            continue
        out.append(f"{org}/{name}")
    return out


def fetch_pin(repo: str) -> str | None:
    try:
        payload = gh_json([
            "api",
            f"repos/{repo}/contents/{PIN_FILENAME}?ref=HEAD",
        ])
    except subprocess.CalledProcessError:
        return None
    import base64
    raw = base64.b64decode(payload["content"]).decode("utf-8")  # type: ignore[index]
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("governance_version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def semver_tuple(version: str) -> tuple[int, int, int, str]:
    core, _, pre = version.lstrip("v").partition("-")
    parts = core.split(".")
    while len(parts) < 3:
        parts.append("0")
    return int(parts[0]), int(parts[1]), int(parts[2]), pre


def is_outdated(current: str | None, new: str) -> bool:
    if current is None:
        return True
    return semver_tuple(current) < semver_tuple(new)


def open_bump_pr(repo: str, new_version: str, dry_run: bool) -> dict[str, str]:
    branch = f"{BRANCH_PREFIX}{new_version}"
    if dry_run:
        return {"repo": repo, "action": "would-open", "branch": branch}
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp) / "repo"
        subprocess.run(["gh", "repo", "clone", repo, str(cwd), "--", "--depth=1"], check=True)
        pin_path = cwd / PIN_FILENAME
        if pin_path.exists():
            content = pin_path.read_text(encoding="utf-8")
            new_lines = []
            for line in content.splitlines():
                if line.strip().startswith("governance_version:"):
                    new_lines.append(f"governance_version: {new_version}")
                else:
                    new_lines.append(line)
            pin_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        else:
            pin_path.write_text(
                "schema: crystal-governance-pin/v1\n"
                f"governance_version: {new_version}\n"
                "source: Malakof/.github\n",
                encoding="utf-8",
            )
        subprocess.run(["git", "checkout", "-b", branch], cwd=cwd, check=True)
        subprocess.run(["git", "add", PIN_FILENAME], cwd=cwd, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: bump governance to {new_version}"],
            cwd=cwd, check=True,
        )
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=cwd, check=True)
        subprocess.run(
            [
                "gh", "pr", "create",
                "--title", f"chore: bump governance to {new_version}",
                "--body", f"Auto-generated PR. Bumps `.crystal-governance.yaml` to `{new_version}`.\n\nReleased from Malakof/.github.",
                "--label", "type:chore",
                "--label", "priority:p2",
            ],
            cwd=cwd, check=True,
        )
    return {"repo": repo, "action": "opened", "branch": branch}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-version", required=True)
    parser.add_argument("--org", default="Malakof")
    parser.add_argument("--include-prefix", default="crystal-")
    parser.add_argument("--exclude-suffix", default="-test,-scratch")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    exclude_suffixes = [s.strip() for s in args.exclude_suffix.split(",") if s.strip()]
    repos = list_target_repos(args.org, args.include_prefix, exclude_suffixes)
    summary = []
    for repo in repos:
        current_pin = fetch_pin(repo)
        if not is_outdated(current_pin, args.new_version):
            summary.append({"repo": repo, "action": "skipped", "current": current_pin})
            continue
        summary.append(open_bump_pr(repo, args.new_version, args.dry_run))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
