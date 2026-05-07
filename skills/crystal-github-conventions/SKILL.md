---
name: crystal-github-conventions
description: Use whenever you create, update, or comment on a GitHub issue, PR, branch, commit, tag, ADR, or PRD in any Crystal repo. Loads the canonical conventions (labels, Conventional Commits, naming, EPIC↔sub-issues workflow) so the artifact passes Malakof/.github enforcement and matches the team's contract.
---

# Crystal GitHub conventions

This skill applies the Crystal team's canonical GitHub conventions defined in
`Malakof/.github/governance/`. Use it **before** writing any GitHub artifact.

## When to invoke

- Drafting a PR title, body, or commit message in a Crystal repo
- Creating an issue (epic, feature, bug, mission intake)
- Choosing labels to apply or migrate
- Naming a branch, tag, ADR, PRD, or workflow
- Setting up a new Crystal repo or onboarding an existing one

## Authoritative sources

The skill defers to the pin version of `Malakof/.github` declared in the target
repo's `.crystal-governance.yaml`:

- `governance/README.md` — narrative reference
- `governance/labels.yaml` — canonical label table
- `governance/scopes.yaml` — Conventional Commits scopes per repo
- `governance/migration-map.yaml` — legacy → canonical renames

If the local repo is missing `.crystal-governance.yaml`, default to `main` of
`Malakof/.github` and emit a structured warning that the repo is not yet
onboarded.

## Pre-flight checks before any artifact

1. **Read the pin** : `cat .crystal-governance.yaml | yq '.governance_version'`.
2. **Resolve the canonical sources** : either fetch from `Malakof/.github` at
   the pin tag, or use the local `.crystal/runtime/governance/` snapshot if
   the `crystal-company` sync has projected one.
3. **Validate against the four packs** below.

## Pack 1 — labels, commits, titles

### Labels (mandatory dimensions)

Every issue/PR must carry exactly one `priority:p*` and one `type:*`. Optional :
`status:*`, `area:*`, `release:*`. Repo-specific extensions (`stream:*`,
`scenario:*`, `agent:*`) only on their target repos. **Never** apply
`crystal:agent|stage|status|runtime|mission|parent|child:*` — those are emitted
exclusively by the paperclip kernel.

### Conventional Commits

```
<type>(<scope>)?: <subject>

[<body>]

[<footer>]
```

Subject : impérative, ≤ 72 chars, no trailing period, lowercase first letter
unless proper noun. Footer keywords : `Closes #N`, `Fixes #N`, `Refs #N`,
`Co-authored-by: …`, `BREAKING CHANGE: …`.

Allowed types : `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`. Scopes per repo come from `scopes.yaml`.

### Issue titles

- `type:epic` → `[EPIC] <subject>`
- otherwise → `<type>: <subject>` (no scope on issues, just on commits/PRs)

### EPIC ↔ sub-issues

Use **GitHub native sub-issues**, never Markdown checklists. The dark-factory
ingestion explicitly fetches via `gh api repos/{owner}/{repo}/issues/{n}/sub_issues`.

## Pack 2 — Git lifecycle

- **Branches** : `<author>/<topic>` for humans, `<agent>/<topic>` for AI agents
  (`codex/…`, `claude/…`, `openhands/…`), `feature/`, `fix/`, `chore/`,
  `release/v<X.Y.Z>`, `hotfix/v<X.Y.Z>-<topic>`. Kebab-case ≤ 60 chars.
- **Tags** : strict SemVer `vX.Y.Z`. Pre-releases `vX.Y.Z-rc.N`,
  `vX.Y.Z-beta.N`, `vX.Y.Z-alpha.N`.
- **Bumps** : `BREAKING CHANGE` or `feat!:` → MAJOR, `feat:` → MINOR,
  `fix:`/`perf:`/`refactor:` → PATCH.

## Pack 3 — Crystal-specific

- **Mission codes** : `<REPO_PREFIX>-<TYPE>-<NUM>` where `REPO_PREFIX` is
  one of `PAUI`, `DFP`, `DFL`, `BEACON`, `SPEC`, `COMP` (see
  `governance/README.md §3.1`), `TYPE` is `FEAT|BUG|SPIKE|DOC|MIGR|OPS`,
  `NUM` is 3-digit zero-padded.
- **Stream codenames** : `atlas`, `beacon`, `forge`, `compass` only. New
  codenames require an ADR.
- **Worktrees** : `/private/tmp/<codename>-<release>`, `~/.codex/worktrees/`,
  `.claude/worktrees/`.
- **Mission stages** (kernel-projected) : `prepare → spec-contract → implement
  → review → ship`. Never set `crystal:stage:*` manually.

## Pack 4 — Infra

- **ADR** : `docs/adr/NNNN-titre-kebab.md`, statuses
  `proposed|accepted|superseded|deprecated`.
- **PRD** : `docs/prd/NNNN-titre-kebab.md`.
- **Workflows** : `<verb>-<object>.yml`. Reusable workflows pinned to a tag
  of `Malakof/.github` (never `@main` in production).
- **Secrets / env** : `CRYSTAL_<DOMAIN>_<PURPOSE>` uppercase + underscores.
- **Repos** : `crystal-<scope>-<purpose>` kebab-case. Scratch repos
  (`*-scratch-*`, `*-test`) archived after 30 days.

## Failure mode (structured refusal)

If the skill cannot resolve `.crystal-governance.yaml` or fetch the pin
version of governance, emit :

```json
{
  "status": "refused",
  "reason": "missing-governance-pin",
  "repo": "<owner>/<repo>",
  "remediation": "Add .crystal-governance.yaml pinning a tag of Malakof/.github (see governance/README.md §6)"
}
```

Do NOT silently fall back to defaults — this matches the project memory
"Prefer structured failure over silent fallback".

## Quick reference

| Artifact | Look at |
|---|---|
| New PR title | Pack 1 §Conventional Commits |
| New issue | Pack 1 §Issue titles + ISSUE_TEMPLATE |
| Choosing labels | `labels.yaml` (filter by `applies_to`) |
| Branch name | Pack 2 §Branches |
| Mission code | Pack 3 §Mission codes |
| ADR/PRD filename | Pack 4 §ADR & PRD |
| Workflow filename | Pack 4 §Workflows |
| Secret name | Pack 4 §Secrets / env |
