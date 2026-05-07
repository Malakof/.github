# Crystal Projects v2 — canonical schema and views

The Crystal mission portfolio is materialised as a single GitHub Projects v2
board: **Crystal Missions** at https://github.com/users/Malakof/projects/1.
This document is the canonical reference for the project's custom fields,
canonical views, and policies.

> **Status**: v1.0.2 — schema codified, views to be created via UI per
> §2 below. Auto-sync from paperclip kernel will land in v1.1.0.

## 1. Custom fields

| Field | Type | Values |
|---|---|---|
| Title | text (default) | issue title |
| Status | single-select (default) | Todo, In Progress, Done |
| Mission code | text | `<REPO_PREFIX>-<TYPE>-<NUM>` (see [`README.md §3.1`](./README.md#31-mission-codes)) |
| Priority | single-select | `p0`, `p1`, `p2`, `p3` |
| Type | single-select | `epic`, `feature`, `bug`, `chore`, `docs`, `refactor`, `spike`, `test` |
| Stream | single-select | `atlas`, `beacon`, `forge`, `compass` |
| Runtime | single-select | `claude`, `codex`, `openhands` |
| Release | text | `v1.0.0`, `v1.0-rc1`, `v2.0`, free form |
| Repository | text (default) | auto from issue source |
| Labels | text (default) | mirrored from the issue |
| Linked pull requests | default | auto |
| Milestone | default | auto |
| Parent issue | default | auto |
| Sub-issues progress | default | auto |

Fields named in the canonical taxonomy mirror the labels documented in
[`labels.yaml`](./labels.yaml). When the paperclip kernel projection is
enabled (v1.1.0+), values are written by the kernel and **never edited
manually**.

## 2. Canonical views

These six views are the supported lenses on the project. They are created
manually via the GitHub UI today; v1.1.0 will provide a script to apply
them via GraphQL.

### View 1 — Operations Kanban (`Status`)

- **Layout**: Board
- **Group by**: Status
- **Sort**: Priority ascending (p0 first)
- **Columns shown**: Title, Mission code, Priority, Type, Repository,
  Assignees
- **Filter**: `is:open` AND (`Type` is not `epic`)
- **Purpose**: daily ops view of in-flight work, excludes EPICs which
  are tracked separately (see View 4).

### View 2 — Priority × Stream (table)

- **Layout**: Table
- **Group by**: Priority
- **Sort**: Stream then Mission code
- **Columns shown**: Title, Mission code, Type, Stream, Runtime, Status,
  Repository
- **Filter**: `is:open`
- **Purpose**: portfolio-wide capacity planning.

### View 3 — Release Roadmap

- **Layout**: Roadmap (or Table grouped by Release if Roadmap not available)
- **Group by**: Release
- **Filter**: `Release` is not empty
- **Purpose**: cross-repo release readiness at a glance.

### View 4 — EPIC tree (Hierarchy)

- **Layout**: Table
- **Filter**: `Type` is `epic` OR `Parent issue` is not empty
- **Group by**: Parent issue (if available) else Repository
- **Sort**: Priority
- **Purpose**: track every EPIC and its native sub-issues progress.

### View 5 — Per Runtime (load balance)

- **Layout**: Board
- **Group by**: Runtime
- **Filter**: `is:open` AND `Status` is not `Done`
- **Sort**: Priority then Mission code
- **Purpose**: see what each runtime (Claude, Codex, OpenHands) is
  currently working on.

### View 6 — Triage queue

- **Layout**: Table
- **Filter**: label `status:triage` OR labels are empty (no `priority:p*`
  AND no `type:*`)
- **Sort**: created date descending
- **Purpose**: catch issues that need product/impl triage.

## 3. Field assignment rules

| Source | Fields written | When |
|---|---|---|
| Issue creator (human) | Title, Type, Priority, Repository (auto) | At creation via ISSUE_TEMPLATE |
| Paperclip kernel (v1.1.0+) | Mission code, Status, Stream, Runtime | On every mission stage transition |
| Dark factory ingestion | Mission code (if not set), Type=epic on parents | At `epic-plan` ingestion |
| GitHub auto | Linked pull requests, Sub-issues progress, Milestone, Parent issue | Continuously |

**Don't edit manually** what the kernel projects (Mission code, Stream,
Runtime, Status when kernel-driven). Manual edits will be overwritten on
the next projection.

## 4. Issue intake into the project

For new repos onboarded after v1.0.2, ensure they are listed in
`scripts/import-issues-to-project.py:REPOS`. New issues created from the
provided ISSUE_TEMPLATE forms are automatically eligible for the project
once added (manually for now via `gh project item-add`, automatically in
v1.1.0).

## 5. Coming in v1.1.0

- Kernel-side projection: paperclip writes to Mission code / Stream /
  Runtime / Status on every stage transition.
- GraphQL view definitions: views above codified as JSON, applied via
  `scripts/setup-project-views.py`.
- `Crystal status` field added to extend the default `Status` with the
  fine-grained `triage`, `ready`, `blocked`, `needs-human` states.
