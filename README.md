# Malakof/.github — Crystal GitHub governance

Single source of truth for Crystal team GitHub conventions:
labels, issue/PR templates, naming, reusable workflows, agent skill.

**Current version**: `v1.0.2` (see `.crystal-governance.yaml`).

## For humans

- **Canonical document**: [`governance/README.md`](./governance/README.md)
- **Label table**: [`governance/labels.yaml`](./governance/labels.yaml)
- **Conventional Commits scopes**: [`governance/scopes.yaml`](./governance/scopes.yaml)

## For AI agents

- **Skill**: [`skills/crystal-github-conventions/SKILL.md`](./skills/crystal-github-conventions/SKILL.md)

Universal `SKILL.md` format (YAML frontmatter `name` + `description`)
recognised by Claude **and** Codex. Automatically propagated by
`crystal-company/builders/sync_repo_surface.py` to both surfaces:

- `.claude/skills/crystal-github-conventions/` — Claude surface
- `.agents/skills/crystal-github-conventions/` — Codex surface (universal skills,
  see [Codex docs](https://developers.openai.com/codex/skills))

> Note: `.codex/agents/` is reserved for Codex **agents** (roles like
> reviewer/CEO/CTO in TOML). Crystal GitHub conventions are a *skill*
> (reference capability), not an agent — so no file in `.codex/agents/`.

## For Crystal repos

Add to the target repo:

1. `.crystal-governance.yaml`:
   ```yaml
   schema: crystal-governance-pin/v1
   governance_version: v1.0.2
   source: Malakof/.github
   ```

2. `.github/workflows/governance-check.yml`:
   ```yaml
   name: governance-check
   on: [push, pull_request]
   jobs:
     check:
       uses: Malakof/.github/.github/workflows/governance-check.yml@v1.0.2
   ```

3. `.github/workflows/enforce-conventions.yml`:
   ```yaml
   name: enforce-conventions
   on: [pull_request]
   jobs:
     enforce:
       uses: Malakof/.github/.github/workflows/enforce-conventions.yml@v1.0.2
   ```

4. Run label sync:
   ```sh
   gh repo clone Malakof/.github /tmp/crystal-governance
   cd /tmp/crystal-governance
   python scripts/sync-labels.py --repo <owner>/<name>
   ```

## Release workflow

On every semver tag `vX.Y.Z` pushed on `main`:

- `.github/workflows/on-release-bump.yml` opens `chore: bump governance
  to vX.Y.Z` PRs on every non-archived `Malakof/crystal-*` repo pinning
  an older version.

## Versioning

- **Major**: label removal, breaking template change.
- **Minor**: label addition, new template/skill/workflow.
- **Patch**: colors, descriptions, doc.

## Structure

```
.
├── README.md                       ← this file
├── .crystal-governance.yaml        ← self-pin
├── governance/
│   ├── README.md                   ← canonical document (4 naming packs)
│   ├── labels.yaml                 ← canonical label table
│   └── scopes.yaml                 ← Conventional Commits scopes
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── epic.yml
│   │   ├── feature.yml
│   │   ├── bug.yml
│   │   ├── mission-intake.yml
│   │   └── config.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── enforce-conventions.yml ← reusable
│       ├── governance-check.yml    ← reusable
│       └── on-release-bump.yml     ← internal (on tag)
├── skills/
│   └── crystal-github-conventions/   ← propagated to .claude/skills + .agents/skills
│       └── SKILL.md
└── scripts/
    ├── sync-labels.py
    ├── setup-autolinks.py
    ├── validate_title.py
    ├── validate_labels.py
    └── open-bump-prs.py
```
