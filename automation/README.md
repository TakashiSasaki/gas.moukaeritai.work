# Automation

`automation/` contains **how synchronization is performed**.

Phase 1 separates synchronization behavior from observed data and materialized project state:

- `shared/` contains repository-access primitives shared by stages.
- `stage-1-inventory/` will own Drive inventory acquisition, project registry reconciliation, and public index generation.
- `stage-2-sync/` will own remote change detection, source synchronization, metadata refresh, and project-state validation.
- `maintenance/` is reserved for explicit historical migrations that must not run as part of steady-state synchronization.

External inventory snapshots belong under `data/`; Apps Script project state belongs under `projects/`; GitHub Pages projections belong under `docs/`.
