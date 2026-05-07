# Crystal GitHub Governance — Doc canonique

Source de vérité unique pour toutes les conventions GitHub Crystal :
labels, templates, naming, workflows. Hébergé dans `Malakof/.github`,
versionné par tags semver, propagé aux repos cibles via pin file
`.crystal-governance.yaml` et `crystal-company/builders/sync_repo_surface.py`.

**Schéma** : `crystal-governance/v1`
**Version** : 1.0.0

---

## 1. Pack Coeur — labels, commits, titres PR/issues

### 1.1 Labels

Voir [`labels.yaml`](./labels.yaml) pour la table canonique complète.

**Règles d'application sur chaque issue/PR :**

- **`priority:p*`** : exactement un, obligatoire.
- **`type:*`** : exactement un, obligatoire.
- **`status:*`** : optionnel — `status:triage` est posé par défaut sur intake.
- **`area:*`** : recommandé, libre `area:<domain-kebab>` si valeur absente.
- **`release:*`** : optionnel, libre `release:<milestone-kebab>`.
- **`stream:*` / `scenario:*` / `agent:*` / `crystal:*` / `mission:*`** : selon le repo (voir `applies_to` dans `labels.yaml`).
- **`crystal:agent|stage|status|runtime|mission|parent|child:*`** : ÉMIS UNIQUEMENT par le kernel paperclip. Ne jamais poser à la main.

**Migration depuis l'historique** : voir [`migration-map.yaml`](./migration-map.yaml).

### 1.2 Conventional Commits

Format strict :

```
<type>(<scope>)?: <subject>

[<body>]

[<footer>]
```

**Types autorisés** : `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
`test`, `build`, `ci`, `chore`, `revert`.

**Scopes** : par repo dans [`scopes.yaml`](./scopes.yaml). Optionnels mais
recommandés pour les repos avec plus d'un domaine fonctionnel.

**Subject** : impératif présent, ≤ 72 caractères, pas de point final,
minuscule au début (sauf nom propre).

**Footer** :
- `Closes #123` / `Fixes #123` pour fermeture auto.
- `Refs #123` pour lien sans fermeture.
- `Co-authored-by: Name <email>` pour co-paternité.
- `BREAKING CHANGE: <description>` pour changements rétro-incompatibles
  (déclenche bump major en SemVer).

**Sign-off** : non requis sauf demande explicite côté repo.

### 1.3 Titres de PR et d'issues

**PR** : strictement Conventional Commits. Le workflow `enforce-conventions`
rejette tout titre non conforme.

**Issue** :
- `type:epic` → préfixe `[EPIC] <subject>` (le préfixe est posé en plus
  du label `type:epic` pour visibilité humaine).
- Tous les autres types → `<type>: <subject>` (subject impératif présent,
  ≤ 80 chars).

**Body** : utiliser les ISSUE_TEMPLATE fournis (epic, feature, bug,
mission-intake). Sections obligatoires : `Context`, `Acceptance criteria`,
`Out of scope`. Sections optionnelles : `Validation`, `Links`.

### 1.4 Workflow EPIC ↔ sub-issues

**Source de vérité** : [GitHub sub-issues natives](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues).

Le template `epic.yml` rappelle de créer les enfants comme sub-issues
(API : `gh api repos/{owner}/{repo}/issues/{n}/sub_issues`). La dark factory
les ingère via la même API (cf. `docs/mvp-milestone-plan.md:74-80` côté
`crystal-dark-factory-poc`).

**Pas de checklist Markdown miroir** : un enfant est une vraie sub-issue,
pas une ligne `- [ ]` dans le body.

---

## 2. Pack Git lifecycle — branches, tags, releases

### 2.1 Branches

| Pattern | Usage |
|---|---|
| `<author>/<topic-kebab>` | Branche humaine de travail (ex: `richard/refactor-auth`). |
| `<agent>/<topic-kebab>` | Branche d'agent IA (ex: `codex/openhands-phase-4-parity`, `claude/spec-review`). |
| `feature/<topic-kebab>` | Branche fonctionnelle longue durée. |
| `fix/<topic-kebab>` | Correctif court. |
| `chore/<topic-kebab>` | Maintenance. |
| `release/v<X>.<Y>.<Z>` | Cut de release. |
| `hotfix/v<X>.<Y>.<Z>-<topic>` | Correctif post-release. |

**Contraintes** : kebab-case, ≤ 60 caractères au total, pas de séparateur
double, pas d'espaces. La branche par défaut reste `main`.

### 2.2 Tags

SemVer strict : `vMAJOR.MINOR.PATCH`. Pre-releases :
`v<X>.<Y>.<Z>-rc.<N>`, `v<X>.<Y>.<Z>-beta.<N>`, `v<X>.<Y>.<Z>-alpha.<N>`.

**Bumps** :
- `BREAKING CHANGE` ou `feat!:` → MAJOR
- `feat:` → MINOR
- `fix:`, `perf:`, `refactor:` → PATCH
- `chore:`, `docs:`, `test:`, `ci:`, `build:`, `style:` → pas de bump (sauf
  si décision explicite côté maintainer).

### 2.3 Releases

- **Changelog** : format [Keep-A-Changelog](https://keepachangelog.com/en/1.1.0/).
- **Release notes** : auto-générées depuis Conventional Commits (workflow
  `release-notes.yml` — fourni en V2).
- **Tag → Release** : chaque tag SemVer publie une release GitHub.
- **Pre-release** : tag avec `-rc.N` / `-beta.N` publie une release marquée
  `prerelease: true`.

---

## 3. Pack Crystal-specific — missions, codenames, worktrees

### 3.1 Mission codes

Format : `<REPO_PREFIX>-<TYPE>-<NUM>`

| Repo | Préfixe |
|---|---|
| `crystal-assistant-ui-poc` | `PAUI` |
| `crystal-dark-factory-poc` | `DFP` |
| `crystal-dark-factory-target-lab` | `DFL` |
| `crystal-discord-bot` | `BEACON` (codename historique) |
| `crystal-specs` | `SPEC` |
| `crystal-company` | `COMP` |

**Types** : `FEAT`, `BUG`, `SPIKE`, `DOC`, `MIGR`, `OPS`.
**Num** : 3 chiffres zero-padded, alloués séquentiellement par repo.

**Exemples** : `PAUI-FEAT-001`, `DFP-BUG-014`, `BEACON-SPIKE-003`.

### 3.2 Stream codenames

Réservés (pas de doublons, ajouts via ADR) :

| Codename | Domaine |
|---|---|
| `atlas` | Operator contracts (Stream A) |
| `beacon` | Discord brain migration (Stream C) |
| `forge` | Durable spine + abstractions (Stream B) |
| `compass` | Cost ledger + onboarding (Stream D) |

Tout nouveau codename doit être validé par ADR avant usage en branche/label.

### 3.3 Worktrees agents

| Pattern | Outil |
|---|---|
| `/private/tmp/<codename>-<release>` | Branches d'agents éphémères pendant un pilote. |
| `~/.codex/worktrees/<codename>` | Worktrees persistants Codex. |
| `.claude/worktrees/<codename>` | Worktrees Claude (locaux au repo). |

### 3.4 Stages canoniques (kernel paperclip)

`prepare → spec-contract → implement → review → ship`

Projetés automatiquement comme labels `crystal:stage:*`. Ne pas poser à la main.

---

## 4. Pack Infra — ADR/PRD, workflows, secrets, repos

### 4.1 ADR & PRD

| Type | Chemin | Format filename |
|---|---|---|
| ADR | `docs/adr/` | `NNNN-titre-kebab.md` (4 chiffres) |
| PRD | `docs/prd/` | `NNNN-titre-kebab.md` (4 chiffres) |

**Statuts ADR** : `proposed | accepted | superseded | deprecated`.
**Template** : voir [`adr-template.md`](./adr-template.md) (à fournir en V1.1).

### 4.2 Workflows GitHub Actions

| Pattern | Exemple |
|---|---|
| `<verb>-<object>.yml` | `enforce-conventions.yml`, `publish-release.yml`, `sync-labels.yml` |
| Reusable workflows | hébergés dans `Malakof/.github/.github/workflows/`, appelés via `uses: Malakof/.github/.github/workflows/<name>.yml@v<X.Y.Z>` |

**Concurrence** : `concurrency: { group: <verb>-<object>-${{ github.ref }}, cancel-in-progress: true }` recommandé.

### 4.3 Secrets

Format : `CRYSTAL_<DOMAIN>_<PURPOSE>` (uppercase, underscores).

| Exemple | Usage |
|---|---|
| `CRYSTAL_DISCORD_BOT_TOKEN` | Token Discord du Beacon. |
| `CRYSTAL_GITHUB_PAT` | PAT pour le sync inter-repos. |
| `CRYSTAL_OPENAI_API_KEY` | Clé OpenAI. |
| `CRYSTAL_ANTHROPIC_API_KEY` | Clé Anthropic. |
| `CRYSTAL_OPS_VPS_SSH` | Clé SSH ops VPS 77.42.86.121. |

**Env vars** : même règle, mêmes préfixes.

### 4.4 Repo names

Pattern : `crystal-<scope>-<purpose>` (kebab-case).

| Exemple | OK |
|---|---|
| `crystal-discord-bot` | ✓ |
| `crystal-assistant-ui-poc` | ✓ |
| `crystal-dark-factory-poc` | ✓ |
| `polaris-scratch-20260416T230130Z` | ✗ (legacy, à archiver après 30j) |

**Visibilité** : par défaut privé. Public uniquement après revue
sécurité/secrets explicite.

**Archivage** : repos `polaris-scratch-*` et `*-test` archivés après
30 jours d'inactivité. Workflow `archive-stale-repos.yml` (fourni en V2)
applique automatiquement.

---

## 5. Versioning de cette gouvernance

- **Source** : `Malakof/.github` repo, branche `main` éditable.
- **Releases** : tags semver `vMAJOR.MINOR.PATCH` sur cette gouvernance.
  - **Major** : breaking change dans labels/templates (suppression de
    label sans alias, changement de namespace).
  - **Minor** : ajout de label/template/skill, changement non breaking.
  - **Patch** : doc, descriptions, couleurs.
- **Pin par repo** : chaque repo Crystal porte `.crystal-governance.yaml`
  qui pin une version :

  ```yaml
  schema: crystal-governance-pin/v1
  governance_version: v1.0.0
  source: Malakof/.github
  ```

- **Bump-PR auto** : à chaque release de `Malakof/.github`, le workflow
  `on-release-bump.yml` ouvre une PR `chore: bump governance to vX.Y.Z`
  sur chaque repo Crystal qui pin une version antérieure.
- **governance-check CI** : workflow réutilisable appelé par chaque repo
  pour vérifier (a) que `governance_version` existe dans `.github`,
  (b) que les labels sont synchronisés, (c) que les templates ne sont pas
  écrasés localement.

---

## 6. Adoption sur un nouveau repo

1. Ajouter `.crystal-governance.yaml` (pin la dernière version stable).
2. Ajouter `.github/workflows/governance-check.yml` qui appelle le reusable.
3. Lancer `gh workflow run governance-check.yml` pour valider.
4. Lancer `python scripts/sync-labels.py --repo <owner>/<repo>` depuis
   `Malakof/.github` pour appliquer la taxonomie canonique.
5. (optionnel) Lancer `migrate-labels.py` si le repo a des labels legacy.

---

## 7. Références

- `labels.yaml` — table canonique des labels
- `migration-map.yaml` — renommages depuis l'historique
- `scopes.yaml` — scopes Conventional Commits par repo
- `.github/ISSUE_TEMPLATE/` — templates issues
- `.github/PULL_REQUEST_TEMPLATE.md` — template PR
- `.github/workflows/enforce-conventions.yml` — validation titre/labels
- `.github/workflows/governance-check.yml` — vérif pin + skills
- `skills/crystal-github-conventions/SKILL.md` — skill agents IA (format universel Claude + Codex, propagé vers `.claude/skills/` et `.agents/skills/`)
