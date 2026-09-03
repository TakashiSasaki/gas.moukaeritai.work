# Google Apps Script Project Management

This repository backs up and version-controls multiple Google Apps Script projects in one Git repository.

各 Google Apps Script project は `projects/<SCRIPT_ID>/` に配置され、Script ID を directory name として使用します。

## Repository Model

The repository separates synchronization responsibilities explicitly:

- `automation/`: synchronization implementation — **how** state is observed and synchronized.
- `data/`: external observations — **what** was observed, including Drive inventory snapshots.
- `projects/`: materialized Apps Script project source and metadata.
- `docs/`: the public GitHub Pages projection, including generated `projects.json`.

## GitHub Actions Workflows

The default branch is `gas.moukaeritai.work`.

### Stage 1: Drive Inventory

Workflow: `.github/workflows/stage-1-inventory.yml`

- **Trigger:** every three hours or manual dispatch.
- **Purpose:** observe Apps Script projects through Drive API, reconcile canonical project registry metadata and lifecycle, and regenerate the public project index.
- **Pipeline:**
  1. `automation/stage-1-inventory/fetch-drive-inventory.py`
  2. `automation/stage-1-inventory/reconcile-project-registry.py`
  3. `automation/stage-1-inventory/generate-public-project-index.py`
  4. repository validation
- **Outputs:** Drive snapshots under `data/inventory/drive-api/snapshots/`, `projects/<SCRIPT_ID>/` registry state, and `docs/projects.json`.

Stage 1 is the authority for Drive-derived project presence. `metadata.json` records this as `lifecycle.driveInventory`:

- `present`: the project exists in the latest Drive inventory and participates in normal publication/synchronization.
- `absent`: the project is missing from the latest Drive inventory. The canonical project directory and source history are retained, but the project is excluded from `docs/projects.json` and normal Stage 2 synchronization. A later Drive observation can return it to `present`.

An `absent` transition is therefore **not** a project deletion.

### Stage 2: Apps Script Synchronization

Workflow: `.github/workflows/stage-2-sync.yml`

- **Trigger:** manual dispatch or successful completion of the Stage 1 workflow.
- **Purpose:** pull changed Apps Script sources and refresh Apps Script/deployment/version/file metadata.
- **Pipeline:**
  1. `automation/stage-2-sync/detect-project-changes.py`
  2. `automation/stage-2-sync/sync-project-source.py`
  3. `automation/stage-2-sync/refresh-project-metadata.py`
  4. `automation/stage-2-sync/validate-project-state.py`
- **External I/O:** Apps Script HTTP access is isolated in `apps_script_api.py`; clasp subprocess/auth-state access is isolated in `clasp_client.py`.

Remote observation and successful source materialization are separate states. `appsScriptApi.updateTime` records observed Apps Script state, while `syncState.lastMaterializedAppsScriptUpdateTime` is the successful-materialization checkpoint used for source freshness. A failed source pull must not advance that checkpoint.

### Phase 2 inspection transition

`automation/stage-2-inspection/` contains the cutover-ready Stage 2 responsibility: read-only Apps Script API inspection and deterministic materialization planning. It directly acquires structured project, file, deployment, and version observations and does **not** invoke clasp or write project source/state. Direct Drive and Apps Script API access share `automation/shared/google_oauth.py`.

This implementation is intentionally not yet wired into the production synchronization workflow. The existing `stage-2-sync` workflow remains authoritative until Stage 3 materialization is introduced and the three-stage workflow cutover is reviewed separately.

### Validation

Workflow: `.github/workflows/validate-automation.yml`

Pull requests are checked with repository structural validation and unit tests under `automation/tests/` without requiring Google credentials.

## Project State

Each tracked project normally contains:

- `.clasp.json` with its Script ID;
- `metadata.json` with namespaced metadata such as `driveApi`, `appsScriptApi`, `lifecycle`, and `syncState`;
- Apps Script source files materialized by Stage 2.

The repository intentionally distinguishes three concepts:

1. Drive observation (`driveApi` and `lifecycle.driveInventory`);
2. Apps Script remote observation (`appsScriptApi` and related remote metadata);
3. successful materialization (`syncState.lastMaterializedAppsScriptUpdateTime`).

Historical metadata/file migrations are explicit maintenance operations under `automation/maintenance/`; they are not part of recurring Stage 1 synchronization.
