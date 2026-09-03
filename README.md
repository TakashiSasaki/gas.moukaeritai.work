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
- **Purpose:** observe Apps Script projects through Drive API, reconcile canonical project registry metadata, and regenerate the public project index.
- **Pipeline:**
  1. `automation/stage-1-inventory/fetch-drive-inventory.py`
  2. `automation/stage-1-inventory/reconcile-project-registry.py`
  3. `automation/stage-1-inventory/generate-public-project-index.py`
  4. repository validation
- **Outputs:** Drive snapshots under `data/inventory/drive-api/snapshots/`, `projects/<SCRIPT_ID>/` registry state, and `docs/projects.json`.

### Stage 2: Apps Script Synchronization

Workflow: `.github/workflows/stage-2-sync.yml`

- **Trigger:** manual dispatch or completion of the Stage 1 workflow.
- **Purpose:** pull changed Apps Script sources and refresh Apps Script/deployment/version/file metadata.
- **Pipeline:**
  1. `automation/stage-2-sync/detect-project-changes.py`
  2. `automation/stage-2-sync/sync-project-source.py`
  3. `automation/stage-2-sync/refresh-project-metadata.py`
  4. `automation/stage-2-sync/validate-project-state.py`
- **External I/O:** Apps Script HTTP access is isolated in `apps_script_api.py`; clasp subprocess/auth-state access is isolated in `clasp_client.py`.

### Validation

Workflow: `.github/workflows/validate-automation.yml`

Pull requests are checked with repository structural validation and unit tests under `automation/tests/` without requiring Google credentials.

## Project State

Each tracked project normally contains:

- `.clasp.json` with its Script ID;
- `metadata.json` with namespaced metadata such as `driveApi` and `appsScriptApi`;
- Apps Script source files materialized by Stage 2.

Historical metadata/file migrations are explicit maintenance operations under `automation/maintenance/`; they are not part of recurring Stage 1 synchronization.
