# Malakof/.github — Crystal GitHub governance

Source de vérité unique pour les conventions GitHub Crystal :
labels, templates issues/PR, naming, workflows réutilisables, skill agents.

**Version courante** : `v1.0.0` (voir `.crystal-governance.yaml`).

## Pour les humains

- **Doc canonique** : [`governance/README.md`](./governance/README.md)
- **Table des labels** : [`governance/labels.yaml`](./governance/labels.yaml)
- **Migration depuis legacy** : [`governance/migration-map.yaml`](./governance/migration-map.yaml)
- **Scopes Conventional Commits** : [`governance/scopes.yaml`](./governance/scopes.yaml)

## Pour les agents IA

- **Skill** : [`skills/crystal-github-conventions/SKILL.md`](./skills/crystal-github-conventions/SKILL.md)

Format universel `SKILL.md` (frontmatter YAML `name` + `description`)
reconnu par Claude **et** Codex. Propagation automatique par
`crystal-company/builders/sync_repo_surface.py` vers les deux surfaces :

- `.claude/skills/crystal-github-conventions/` — surface Claude
- `.agents/skills/crystal-github-conventions/` — surface Codex (skills universels,
  cf. [doc Codex](https://developers.openai.com/codex/skills))

> Note : `.codex/agents/` est réservé aux **agents** Codex (rôles type
> reviewer/CEO/CTO en TOML). Les conventions GitHub Crystal sont un
> *skill* (capacité référence), pas un agent — donc pas de fichier dans
> `.codex/agents/`.

## Pour les repos Crystal

Ajoute dans le repo cible :

1. `.crystal-governance.yaml` :
   ```yaml
   schema: crystal-governance-pin/v1
   governance_version: v1.0.0
   source: Malakof/.github
   ```

2. `.github/workflows/governance-check.yml` :
   ```yaml
   name: governance-check
   on: [push, pull_request]
   jobs:
     check:
       uses: Malakof/.github/.github/workflows/governance-check.yml@v1.0.0
   ```

3. `.github/workflows/enforce-conventions.yml` :
   ```yaml
   name: enforce-conventions
   on: [pull_request]
   jobs:
     enforce:
       uses: Malakof/.github/.github/workflows/enforce-conventions.yml@v1.0.0
   ```

4. Lance le sync labels :
   ```sh
   gh repo clone Malakof/.github /tmp/crystal-governance
   cd /tmp/crystal-governance
   python scripts/sync-labels.py --repo <owner>/<name>
   python scripts/migrate-labels.py --repo <owner>/<name> --dry-run
   python scripts/migrate-labels.py --repo <owner>/<name>  # apply
   ```

## Workflow de release

À chaque tag semver `vX.Y.Z` poussé sur `main` de ce repo :

- `.github/workflows/on-release-bump.yml` ouvre des PRs `chore: bump
  governance to vX.Y.Z` sur tous les repos `Malakof/crystal-*` non archivés
  qui pinent une version antérieure.

## Versioning

- **Major** : suppression de label, breaking template change.
- **Minor** : ajout de label, nouveau template/skill/workflow.
- **Patch** : couleurs, descriptions, doc.

## Structure

```
.
├── README.md                       ← ce fichier
├── .crystal-governance.yaml        ← self-pin
├── governance/
│   ├── README.md                   ← doc canonique (4 packs nommage)
│   ├── labels.yaml                 ← table canonique
│   ├── migration-map.yaml          ← renommages legacy → canonique
│   └── scopes.yaml                 ← scopes Conventional Commits
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
│       └── on-release-bump.yml     ← interne (sur tag)
├── skills/
│   └── crystal-github-conventions/   ← propagé vers .claude/skills + .agents/skills
│       └── SKILL.md
└── scripts/
    ├── sync-labels.py
    ├── migrate-labels.py
    ├── validate_title.py
    ├── validate_labels.py
    └── open-bump-prs.py
```
