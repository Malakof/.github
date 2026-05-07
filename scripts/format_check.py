#!/usr/bin/env python3
"""Validate a PR or issue against Crystal governance via GitHub Models LLM.

Reads:
- governance/labels.yaml + governance/scopes.yaml + skills/crystal-github-conventions/SKILL.md
- The PR or issue title, body, labels via gh CLI
- Calls GitHub Models (openai/gpt-4o-mini by default) with a strict system prompt
- Receives a JSON verdict {pass: bool, severity: ok|warn|fail, findings: [...]}
- Posts a single sticky comment on the PR/issue with the result
- Exits 0 if pass or warn, 1 if fail and --blocking true

Usage:
    python format_check.py --repo <owner>/<name> --pr <number> [--blocking false|true]
    python format_check.py --repo <owner>/<name> --issue <number> [--blocking false|true]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://models.github.ai/inference/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"
COMMENT_MARKER = "<!-- crystal-format-check -->"


def gh_json(args: list[str]) -> object:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"_error": result.stderr.strip()[:300]}
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def load_governance(governance_root: Path) -> dict[str, str]:
    pieces = {
        "labels_yaml": (governance_root / "governance" / "labels.yaml").read_text(encoding="utf-8"),
        "scopes_yaml": (governance_root / "governance" / "scopes.yaml").read_text(encoding="utf-8"),
        "skill_md": (governance_root / "skills" / "crystal-github-conventions" / "SKILL.md").read_text(encoding="utf-8"),
    }
    return pieces


def fetch_artifact(repo: str, number: int, kind: str) -> dict:
    fields = "title,body,labels,number,url"
    if kind == "pr":
        fields += ",author"
        cmd = ["pr", "view", str(number), "--repo", repo, "--json", fields]
    else:
        cmd = ["issue", "view", str(number), "--repo", repo, "--json", fields]
    payload = gh_json(cmd) or {}
    return payload if isinstance(payload, dict) else {}


def build_prompts(governance: dict[str, str], artifact: dict, kind: str, repo: str) -> tuple[str, str]:
    system = (
        "You are Crystal Governance Validator, a strict linter for GitHub artifacts in the Crystal team. "
        "You receive a Crystal PR or issue and the canonical conventions. "
        "Validate against the conventions and return ONLY a JSON object matching the schema below. "
        "Do not include any prose outside the JSON.\n\n"
        "Schema:\n"
        "{\n"
        '  "pass": boolean,\n'
        '  "severity": "ok" | "warn" | "fail",\n'
        '  "summary": "one-sentence verdict",\n'
        '  "findings": [\n'
        '    {"rule": "string", "severity": "ok|warn|fail", "message": "string", "remediation": "string|null"}\n'
        "  ]\n"
        "}\n\n"
        "Rules to check:\n"
        "1. Title format: Conventional Commits `<type>(<scope>)?: <subject>` for PRs; "
        "`<type>: <subject>` for issues; `[EPIC] <subject>` for epics.\n"
        "2. Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.\n"
        "3. Subject ≤ 72 chars (PR) or ≤ 80 chars (issue), imperative present, lowercase first letter, no trailing period.\n"
        "4. Scope (when present in PR title) must belong to scopes.yaml entry for the repo (or universal_scopes).\n"
        "5. Labels must include exactly one priority:p* (p0|p1|p2|p3) AND one type:* matching the title type.\n"
        "6. Labels crystal:agent|stage|status|runtime|mission|parent|child:* are kernel-projected and must NOT be set manually unless author is paperclip-bot.\n"
        "7. Body should have sections (issues only): Context, Acceptance criteria, Out of scope. Missing => warn.\n"
        "8. Discourage Markdown checklists like `- [ ] #N` for sub-issues — should use GitHub native sub-issues. Warn if detected.\n\n"
        "Severity policy:\n"
        "- 'fail' for clear violations (broken Conventional Commits format, wrong type, missing required label).\n"
        "- 'warn' for missing optional sections, soft hints, deprecations.\n"
        "- 'ok' overall when no fail and no warn; pass=true.\n"
        "- pass=false if any 'fail' finding exists, otherwise pass=true.\n"
    )
    user = (
        f"Repository: {repo}\n"
        f"Artifact kind: {kind}\n\n"
        f"=== labels.yaml (canonical, excerpt of categories) ===\n{governance['labels_yaml']}\n\n"
        f"=== scopes.yaml ===\n{governance['scopes_yaml']}\n\n"
        f"=== artifact ===\n{json.dumps(artifact, indent=2)}\n"
    )
    return system, user


def call_llm(token: str, system: str, user: str, model: str) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    req = urllib.request.Request(ENDPOINT, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "pass": False,
            "severity": "warn",
            "summary": f"LLM endpoint returned HTTP {exc.code}; skipping check.",
            "findings": [{
                "rule": "infra:llm-error",
                "severity": "warn",
                "message": exc.read().decode("utf-8", errors="replace")[:300],
                "remediation": None,
            }],
        }
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


def render_comment(verdict: dict, model: str) -> str:
    sev = verdict.get("severity", "warn")
    icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(sev, "❔")
    lines = [
        COMMENT_MARKER,
        f"## {icon} Crystal format check — {sev.upper()}",
        "",
        f"**{verdict.get('summary', '(no summary)')}**",
        "",
    ]
    findings = verdict.get("findings") or []
    if findings:
        lines.append("### Findings")
        lines.append("")
        for f in findings:
            f_sev = f.get("severity", "warn")
            f_icon = {"ok": "✓", "warn": "⚠️", "fail": "✗"}.get(f_sev, "•")
            lines.append(f"- {f_icon} **{f.get('rule', 'rule')}** — {f.get('message', '')}")
            rem = f.get("remediation")
            if rem:
                lines.append(f"  - _Remediation:_ {rem}")
        lines.append("")
    lines.append(f"_Validated against [Crystal governance](https://github.com/Malakof/.github) using `{model}` via GitHub Models._")
    return "\n".join(lines)


def upsert_comment(repo: str, number: int, kind: str, body: str) -> None:
    issues_or_pr_endpoint = f"repos/{repo}/issues/{number}/comments"
    existing = gh_json(["api", issues_or_pr_endpoint, "--paginate"]) or []
    if not isinstance(existing, list):
        existing = []
    sticky_id = None
    for c in existing:
        if isinstance(c, dict) and COMMENT_MARKER in (c.get("body") or ""):
            sticky_id = c.get("id")
            break
    if sticky_id:
        subprocess.run(
            ["gh", "api", "--method", "PATCH", f"repos/{repo}/issues/comments/{sticky_id}",
             "-f", f"body={body}"],
            check=False, capture_output=True, text=True,
        )
    else:
        subprocess.run(
            ["gh", "api", "--method", "POST", issues_or_pr_endpoint,
             "-f", f"body={body}"],
            check=False, capture_output=True, text=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, default=None)
    parser.add_argument("--issue", type=int, default=None)
    parser.add_argument("--governance-root", default=".governance", type=Path)
    parser.add_argument("--blocking", default="false")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-comment", action="store_true")
    args = parser.parse_args()

    if (args.pr is None) == (args.issue is None):
        parser.error("Provide exactly one of --pr or --issue.")

    kind = "pr" if args.pr is not None else "issue"
    number = args.pr if args.pr is not None else args.issue
    blocking = args.blocking.lower() == "true"

    artifact = fetch_artifact(args.repo, number, kind)
    if "_error" in artifact:
        print(f"::error::Failed to fetch {kind} #{number}: {artifact['_error']}")
        return 1

    governance = load_governance(args.governance_root)
    system, user = build_prompts(governance, artifact, kind, args.repo)

    token = os.environ.get("GH_MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("::error::No GITHUB_TOKEN / GH_MODELS_TOKEN / GH_TOKEN available for GitHub Models call.")
        return 1

    verdict = call_llm(token, system, user, args.model)
    body = render_comment(verdict, args.model)

    print(json.dumps(verdict, indent=2))

    if not args.no_comment:
        upsert_comment(args.repo, number, kind, body)

    sev = verdict.get("severity", "warn")
    if sev == "fail" and blocking:
        print(f"::error::Format check FAILED on {kind} #{number} (blocking=true).")
        return 1
    if sev == "fail":
        print(f"::warning::Format check FAILED on {kind} #{number} (non-blocking).")
    elif sev == "warn":
        print(f"::warning::Format check WARN on {kind} #{number}.")
    else:
        print(f"::notice::Format check OK on {kind} #{number}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
