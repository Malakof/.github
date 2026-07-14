#!/usr/bin/env python3
"""Open `chore: 🧹 bump governance to vX.Y.Z` PRs across Crystal repos.

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
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PIN_FILENAME = ".crystal-governance.yaml"
BRANCH_PREFIX = "chore/bump-governance-"
SCRIPT_DIR = Path(__file__).resolve().parent
LABELS_FILE = SCRIPT_DIR.parent / "governance" / "labels.yaml"
PR_LABELS = ["type:chore", "priority:p2"]
WORKFLOW_REF_RE = re.compile(
    r"(Malakof/\.github/\.github/workflows/[^@\s]+\.yml@)(v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?|main)"
)


def bump_pr_title(version: str) -> str:
    return f"chore: 🧹 bump governance to {version}"


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


def bump_workflow_refs(repo_path: Path, new_version: str) -> list[str]:
    workflow_root = repo_path / ".github" / "workflows"
    if not workflow_root.exists():
        return []
    changed: list[str] = []
    for path in sorted(workflow_root.glob("*.yml")):
        content = path.read_text(encoding="utf-8")
        updated = WORKFLOW_REF_RE.sub(rf"\g<1>{new_version}", content)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path.relative_to(repo_path)))
    return changed


def sync_target_labels(repo: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "sync-labels.py"),
            "--repo",
            repo,
            "--labels-file",
            str(LABELS_FILE),
        ],
        check=True,
    )


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
        workflow_changes = bump_workflow_refs(cwd, new_version)
        subprocess.run(["git", "checkout", "-b", branch], cwd=cwd, check=True)
        subprocess.run(
            ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
            cwd=cwd, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "github-actions[bot]"],
            cwd=cwd, check=True,
        )
        add_paths = [PIN_FILENAME]
        if (cwd / ".github" / "workflows").exists():
            add_paths.append(".github/workflows")
        subprocess.run(["git", "add", *add_paths], cwd=cwd, check=True)
        diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=cwd, check=False)
        if diff_check.returncode == 0:
            return {"repo": repo, "action": "skipped", "current": new_version, "branch": branch}
        subprocess.run(
            ["git", "commit", "-m", bump_pr_title(new_version)],
            cwd=cwd, check=True,
        )
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=cwd, check=True)
        sync_target_labels(repo)
        pr_args = [
            "gh", "pr", "create",
            "--repo", repo,
            "--head", branch,
            "--title", bump_pr_title(new_version),
            "--body",
            (
                f"Auto-generated PR. Bumps `.crystal-governance.yaml` to `{new_version}` "
                "and updates reusable Malakof/.github workflow refs when present.\n\n"
                f"Workflow refs updated: {', '.join(workflow_changes) if workflow_changes else 'none'}.\n\n"
                "Released from Malakof/.github."
            ),
        ]
        label_args = [arg for label in PR_LABELS for arg in ("--label", label)]
        subprocess.run(pr_args + label_args, cwd=cwd, check=True)
    return {"repo": repo, "action": "opened", "branch": branch}


DEFAULT_REPOS = [
    "Malakof/crystal-capabilities",
    "Malakof/crystal-dark-factory-poc",
    "Malakof/crystal-dark-factory-target-lab",
    "Malakof/crystal-discord-bot",
    "Malakof/crystal-specs",
    "Malakof/crystal-assistant-ui-poc",
    "Malakof/crystal-company",
    "Malakof/crystal-compta",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-version", required=True)
    parser.add_argument("--org", default="Malakof")
    parser.add_argument("--repos", default=",".join(DEFAULT_REPOS),
                        help="Comma-separated explicit list. Defaults to the 6 Crystal governed repos.")
    parser.add_argument("--include-prefix", default=None,
                        help="Optional glob prefix override (legacy mode).")
    parser.add_argument("--exclude-suffix", default="-test,-scratch")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Configure git to use gh's token for HTTPS pushes (no-op locally if already set).
    if not args.dry_run:
        subprocess.run(["gh", "auth", "setup-git"], check=False)

    if args.include_prefix:
        exclude_suffixes = [s.strip() for s in args.exclude_suffix.split(",") if s.strip()]
        repos = list_target_repos(args.org, args.include_prefix, exclude_suffixes)
    else:
        repos = [r.strip() for r in args.repos.split(",") if r.strip()]

    summary = []
    for repo in repos:
        try:
            current_pin = fetch_pin(repo)
            if not is_outdated(current_pin, args.new_version):
                summary.append({"repo": repo, "action": "skipped", "current": current_pin})
                continue
            summary.append(open_bump_pr(repo, args.new_version, args.dry_run))
        except subprocess.CalledProcessError as exc:
            summary.append({
                "repo": repo,
                "action": "error",
                "command": " ".join(exc.cmd) if exc.cmd else "?",
                "stderr": (exc.stderr or "")[:200] if isinstance(exc.stderr, str) else "",
            })
    print(json.dumps(summary, indent=2))
    # Exit 0 even on per-repo errors — telemetry is in summary.
    return 0


if __name__ == "__main__":
    sys.exit(main())
