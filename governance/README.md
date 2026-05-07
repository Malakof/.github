# Crystal GitHub Governance — Canonical Document

Single source of truth for all Crystal team GitHub conventions:
labels, templates, naming, workflows. Hosted in `Malakof/.github`,
versioned by semver tags, propagated to target repos via the pin file
`.crystal-governance.yaml` and `crystal-company/builders/sync_repo_surface.py`.

**Schema**: `crystal-governance/v1`
**Version**: 1.0.0

---

## 1. Core Pack — labels, commits, PR/issue titles

### 1.1 Labels

See [`labels.yaml`](./labels.yaml) for the full canonical table.

**Application rules on every issue/PR:**

- **`priority:p*`**: exactly one, mandatory.
- **`type:*`**: exactly one, mandatory.
- **`status:*`**: optional — `status:triage` is set by default on intake.
- **`area:*`**: recommended, free-form `area:<domain-kebab>` if no preset matches.
- **`release:*`**: optional, free-form `release:<milestone-kebab>`.
- **`stream:*` / `scenario:*` / `agent:*` / `crystal:*` / `mission:*`**: per repo (see `applies_to` in `labels.yaml`).
- **`crystal:agent|stage|status|runtime|mission|parent|child:*`**: EMITTED ONLY by paperclip kernel. Never set manually.

### 1.2 Conventional Commits

Strict format:

```
<type>(<scope>)?: <subject>

[<body>]

[<footer>]
```

**Allowed types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, `revert`.

**Scopes**: per repo in [`scopes.yaml`](./scopes.yaml). Optional but
recommended on repos with multiple functional domains.

**Subject**: imperative present, ≤ 72 chars, no trailing period,
lowercase first letter (unless proper noun).

**Footer**:
- `Closes #123` / `Fixes #123` for auto-close.
- `Refs #123` for link without close.
- `Co-authored-by: Name <email>` for co-authorship.
- `BREAKING CHANGE: <description>` for backwards-incompatible changes
  (triggers MAJOR bump in SemVer).

**Sign-off**: not required unless explicitly requested per repo.

### 1.3 PR and issue titles

**PR**: strict Conventional Commits. The `enforce-conventions` workflow
rejects any non-conforming title.

**Issue**:
- `type:epic` → prefix `[EPIC] <subject>` (the prefix is set in addition
  to the `type:epic` label for human visibility).
- All other types → `<type>: <subject>` (imperative present subject,
  ≤ 80 chars).

**Body**: use the provided ISSUE_TEMPLATE (epic, feature, bug,
mission-intake). Required sections: `Context`, `Acceptance criteria`,
`Out of scope`. Optional sections: `Validation`, `Links`.

### 1.4 EPIC ↔ sub-issues workflow

**Source of truth**: [GitHub native sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues).

The `epic.yml` template reminds to create children as native sub-issues
(API: `gh api repos/{owner}/{repo}/issues/{n}/sub_issues`). The dark
factory ingests them via the same API.

**No mirror Markdown checklist**: a child is a real sub-issue,
not a `- [ ]` line in the body.

---

## 2. Git Lifecycle Pack — branches, tags, releases

### 2.1 Branches

| Pattern | Use |
|---|---|
| `<author>/<topic-kebab>` | Human work branch (e.g. `richard/refactor-auth`). |
| `<agent>/<topic-kebab>` | AI agent branch (e.g. `codex/openhands-phase-4-parity`, `claude/spec-review`). |
| `feature/<topic-kebab>` | Long-running feature branch. |
| `fix/<topic-kebab>` | Short fix. |
| `chore/<topic-kebab>` | Maintenance. |
| `release/v<X>.<Y>.<Z>` | Release cut. |
| `hotfix/v<X>.<Y>.<Z>-<topic>` | Post-release fix. |

**Constraints**: kebab-case, ≤ 60 chars total, no double separators,
no spaces. Default branch remains `main`.

### 2.2 Tags

Strict SemVer: `vMAJOR.MINOR.PATCH`. Pre-releases:
`v<X>.<Y>.<Z>-rc.<N>`, `v<X>.<Y>.<Z>-beta.<N>`, `v<X>.<Y>.<Z>-alpha.<N>`.

**Bumps**:
- `BREAKING CHANGE` or `feat!:` → MAJOR
- `feat:` → MINOR
- `fix:`, `perf:`, `refactor:` → PATCH
- `chore:`, `docs:`, `test:`, `ci:`, `build:`, `style:` → no bump (unless
  explicit maintainer decision).

### 2.3 Releases

- **Changelog**: [Keep-A-Changelog](https://keepachangelog.com/en/1.1.0/) format.
- **Release notes**: auto-generated from Conventional Commits (workflow
  `release-notes.yml` — provided in V2).
- **Tag → Release**: every SemVer tag publishes a GitHub release.
- **Pre-release**: tag with `-rc.N` / `-beta.N` publishes a release marked
  `prerelease: true`.

---

## 3. Crystal-specific Pack — missions, codenames, worktrees

### 3.1 Mission codes

Format: `<REPO_PREFIX>-<TYPE>-<NUM>`

| Repo | Prefix |
|---|---|
| `crystal-assistant-ui-poc` | `PAUI` |
| `crystal-dark-factory-poc` | `DFP` |
| `crystal-dark-factory-target-lab` | `DFL` |
| `crystal-discord-bot` | `BEACON` (historical codename) |
| `crystal-specs` | `SPEC` |
| `crystal-company` | `COMP` |

**Types**: `FEAT`, `BUG`, `SPIKE`, `DOC`, `MIGR`, `OPS`.
**Num**: 3-digit zero-padded, allocated sequentially per repo.

**Examples**: `PAUI-FEAT-001`, `DFP-BUG-014`, `BEACON-SPIKE-003`.

### 3.2 Stream codenames

Reserved (no duplicates, additions via ADR):

| Codename | Domain |
|---|---|
| `atlas` | Operator contracts (Stream A) |
| `beacon` | Discord brain migration (Stream C) |
| `forge` | Durable spine + abstractions (Stream B) |
| `compass` | Cost ledger + onboarding (Stream D) |

Any new codename must be validated by ADR before use in branches/labels.

### 3.3 Agent worktrees

| Pattern | Tool |
|---|---|
| `/private/tmp/<codename>-<release>` | Ephemeral agent branches during a pilot. |
| `~/.codex/worktrees/<codename>` | Persistent Codex worktrees. |
| `.claude/worktrees/<codename>` | Claude worktrees (repo-local). |

### 3.4 Canonical stages (paperclip kernel)

`prepare → spec-contract → implement → review → ship`

Projected automatically as `crystal:stage:*` labels. Never set manually.

---

## 4. Infra Pack — ADR/PRD, workflows, secrets, repos

### 4.1 ADR & PRD

| Type | Path | Filename format |
|---|---|---|
| ADR | `docs/adr/` | `NNNN-title-kebab.md` (4 digits) |
| PRD | `docs/prd/` | `NNNN-title-kebab.md` (4 digits) |

**ADR statuses**: `proposed | accepted | superseded | deprecated`.

### 4.2 GitHub Actions workflows

| Pattern | Example |
|---|---|
| `<verb>-<object>.yml` | `enforce-conventions.yml`, `publish-release.yml`, `sync-labels.yml` |
| Reusable workflows | hosted in `Malakof/.github/.github/workflows/`, called via `uses: Malakof/.github/.github/workflows/<name>.yml@v<X.Y.Z>` |

**Concurrency**: `concurrency: { group: <verb>-<object>-${{ github.ref }}, cancel-in-progress: true }` recommended.

### 4.3 Secrets

Format: `CRYSTAL_<DOMAIN>_<PURPOSE>` (uppercase, underscores).

| Example | Use |
|---|---|
| `CRYSTAL_DISCORD_BOT_TOKEN` | Beacon Discord token. |
| `CRYSTAL_GITHUB_PAT` | PAT for cross-repo sync. |
| `CRYSTAL_OPENAI_API_KEY` | OpenAI key. |
| `CRYSTAL_ANTHROPIC_API_KEY` | Anthropic key. |
| `CRYSTAL_OPS_VPS_SSH` | VPS ops SSH key. |

**Env vars**: same rule, same prefixes.

### 4.4 Repo names

Pattern: `crystal-<scope>-<purpose>` (kebab-case).

| Example | OK |
|---|---|
| `crystal-discord-bot` | ✓ |
| `crystal-assistant-ui-poc` | ✓ |
| `crystal-dark-factory-poc` | ✓ |
| `polaris-scratch-20260416T230130Z` | ✗ (legacy, archive after 30d) |

**Visibility**: private by default. Public only after explicit
security/secrets review.

**Archival**: scratch and `*-test` repos archived after 30 days of
inactivity.

---

## 5. Governance versioning

- **Source**: `Malakof/.github` repo, editable on `main`.
- **Releases**: SemVer tags `vMAJOR.MINOR.PATCH` on this governance.
  - **Major**: breaking change in labels/templates (label removal without
    alias, namespace change).
  - **Minor**: addition of label/template/skill, non-breaking change.
  - **Patch**: doc, descriptions, colors.
- **Per-repo pin**: each Crystal repo carries `.crystal-governance.yaml`
  pinning a version:

  ```yaml
  schema: crystal-governance-pin/v1
  governance_version: v1.0.0
  source: Malakof/.github
  ```

- **Auto bump-PR**: on every `Malakof/.github` release, the
  `on-release-bump.yml` workflow opens a `chore: bump governance to vX.Y.Z`
  PR on each Crystal repo pinning an older version.
- **governance-check CI**: reusable workflow called from each repo to
  verify (a) `governance_version` exists in `.github`, (b) labels are in
  sync, (c) templates are not overridden locally.

---

## 6. Adoption on a new repo

1. Add `.crystal-governance.yaml` (pin the latest stable version).
2. Add `.github/workflows/governance-check.yml` calling the reusable.
3. Run `gh workflow run governance-check.yml` to validate.
4. Run `python scripts/sync-labels.py --repo <owner>/<repo>` from
   `Malakof/.github` to apply the canonical taxonomy.

---

## 7. References

- `labels.yaml` — canonical label table
- `scopes.yaml` — Conventional Commits scopes per repo
- `.github/ISSUE_TEMPLATE/` — issue templates
- `.github/PULL_REQUEST_TEMPLATE.md` — PR template
- `.github/workflows/enforce-conventions.yml` — title/labels validation
- `.github/workflows/governance-check.yml` — pin + skills check
- `skills/crystal-github-conventions/SKILL.md` — AI agents skill (universal Claude + Codex format, propagated to `.claude/skills/` and `.agents/skills/`)
