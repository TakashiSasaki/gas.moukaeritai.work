# Instructions for AI Agents

This repository stores and synchronizes many Google Apps Script projects in one Git repository.

## General Guidelines

1. Treat `projects/<SCRIPT_ID>/` as the only canonical location for materialized Apps Script project state.
2. Keep original Apps Script filenames whenever possible, including `Code.js`, `appsscript.json`, HTML files, and project-specific names.
3. Use the existing automation under `automation/` rather than inventing parallel synchronization scripts.
4. Do not manually edit generated inventory snapshots or `docs/projects.json` when the canonical automation can produce them.
5. Keep `README.md`, this file, and `docs/AGENTS.md` aligned with repository-level workflow changes.
6. Preserve actionable error output around clasp, Google APIs, authentication, JSON parsing, and filesystem operations.

## Repository Structure and Authority

- `automation/`: **how synchronization is performed**.
  - `stage-1-inventory/`: Drive inventory acquisition, canonical registry/lifecycle reconciliation, and public project-index generation.
  - `stage-2-inspection/`: Phase 2 read-only Apps Script API inspection and deterministic materialization planning; this implementation must not invoke clasp or mutate project source/state.
  - `stage-2-sync/`: currently orchestrated compatibility path combining Apps Script change detection, clasp source synchronization, metadata refresh, and project-state validation until the three-stage cutover.
  - `shared/`: repository, OAuth, and validation primitives shared by stages.
  - `maintenance/`: explicit historical migrations; these are not part of steady-state synchronization.
- `data/`: **what was externally observed**. Drive inventory snapshots live under `data/inventory/drive-api/snapshots/`.
- `projects/`: materialized Apps Script project state under `projects/<SCRIPT_ID>/`.
- `docs/`: GitHub Pages/public projection. Local rules live in `docs/AGENTS.md`.
- `.github/workflows/`: orchestration only; business logic belongs under `automation/`.

There is no supported repository-root project fallback. Do not recreate one.

The canonical state authorities are intentionally distinct:

- Stage 1 / Drive owns `driveApi` and `lifecycle.driveInventory`.
- Apps Script remote observation belongs under `appsScriptApi` and the related remote metadata namespaces.
- `syncState.lastMaterializedAppsScriptUpdateTime` records the Apps Script state that was **successfully materialized**, not merely observed.

Never infer successful synchronization solely from a freshly observed remote timestamp.

Direct Drive API and Apps Script API code must acquire bearer tokens through `automation/shared/google_oauth.py`. That provider may read clasp-compatible authorized-user credentials but must not use `clasp list` or mutate clasp's credential store to refresh direct-API access. clasp commands remain responsible for their own OAuth lifecycle.

## Synchronization Workflows

### Stage 1 — inventory

`.github/workflows/stage-1-inventory.yml` runs every three hours and can also be dispatched manually. Its canonical sequence is:

1. `automation/stage-1-inventory/fetch-drive-inventory.py`
2. `automation/stage-1-inventory/reconcile-project-registry.py`
3. `automation/stage-1-inventory/generate-public-project-index.py`
4. repository validation

Stage 1 owns Drive observation, `driveApi` reconciliation, and Drive-derived lifecycle. It must not absorb Apps Script source pulling, deployment/version refresh, or historical migration.

`lifecycle.driveInventory` has two states:

- `present`: observed in the latest Drive inventory and eligible for normal publication/synchronization.
- `absent`: not observed in the latest Drive inventory. Preserve the entire `projects/<SCRIPT_ID>/` directory and source history, omit the project from the public index and normal downstream synchronization, and allow a later observation to return it to `present`.

Do not treat `absent` as authorization to delete source or the project directory.

### Current Stage 2 — compatibility synchronization

`.github/workflows/stage-2-sync.yml` can be dispatched manually and is triggered only after successful Stage 1 completion. Until the three-stage workflow cutover, its canonical sequence remains:

1. `automation/stage-2-sync/detect-project-changes.py`
2. `automation/stage-2-sync/sync-project-source.py`
3. `automation/stage-2-sync/refresh-project-metadata.py`
4. `automation/stage-2-sync/validate-project-state.py`

External Apps Script HTTP I/O in this compatibility path goes through its `apps_script_api.py`; clasp subprocess/auth-state I/O goes through `clasp_client.py`. Keep business decisions out of those I/O primitives.

Source freshness is compared against `syncState.lastMaterializedAppsScriptUpdateTime`. During migration, older metadata may use the previously successful `appsScriptApi.updateTime` as the fallback checkpoint. A failed source pull must leave the materialization checkpoint unchanged; only a successful source synchronization may advance it.

### Target Stage 2 — inspection/planning

`automation/stage-2-inspection/` is the cutover-ready Stage 2 implementation. It must:

1. use the Google Apps Script API directly for project metadata, file metadata, deployments, and versions;
2. skip projects whose Drive lifecycle is `absent`;
3. emit a deterministic JSON materialization plan;
4. remain read-only with respect to `projects/<SCRIPT_ID>/`;
5. fail closed when required Apps Script API observations cannot be obtained;
6. never invoke clasp or parse human-readable clasp output.

This implementation is additive until Stage 3 exists. Do not wire it into the production workflow or remove the compatibility path before the dedicated cutover PR.

## Project Directory Rules

1. Do not rename or flatten `projects/<SCRIPT_ID>/`.
2. Keep `.clasp.json` in each tracked project directory with the correct non-empty `scriptId`.
3. Preserve unrelated namespaces in `metadata.json`. In particular, Stage 1 and Stage 2 must not overwrite each other's authoritative metadata blocks.
4. Treat standalone `deployments.json`, `versions.json`, and their old text variants as legacy state, not as canonical outputs.
5. Be careful with case-insensitive filename collisions because this repository is actively used on Windows.
6. Never advance `syncState.lastMaterializedAppsScriptUpdateTime` for a failed or unattempted source synchronization.

## Project Creation and Deletion

- Creation: create only under `projects/<SCRIPT_ID>/` and initialize `.clasp.json` consistently with that Script ID.
- Lifecycle absence: a project missing from Drive is marked `lifecycle.driveInventory = "absent"`; retain its canonical directory and source history.
- Deletion: deleting a project directory is a separate destructive operation. Confirm the intended project before removing `projects/<SCRIPT_ID>/` and related generated references.
- Historical schema/file migration belongs in explicit maintenance tooling, not in recurring Stage 1 logic.

## Docs and Web UI

1. `docs/` is production public content for `https://gas.moukaeritai.work/`.
2. `docs/projects.json` is generated by `automation/stage-1-inventory/generate-public-project-index.py`; it contains only projects eligible under the current Drive lifecycle and must not be hand-maintained during normal synchronization.
3. Read `docs/AGENTS.md` before changing public site behavior or assets.

## Validation

Run `.github/scripts/validate-automation.py` and the unit tests under `automation/tests/` for repository automation changes. The validation workflow is `.github/workflows/validate-automation.yml`.

When changing synchronization semantics, preserve the separation between external observation, materialized project state, successful-materialization checkpoints, and public projection unless the repository architecture is intentionally being redesigned.
