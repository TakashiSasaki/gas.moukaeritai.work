# Automation

`automation/` contains **how synchronization is performed**.

The synchronization architecture separates implementation from observed data and materialized project state:

- `shared/` contains repository-access primitives shared by stages.
- `stage-1-inventory/` owns Drive inventory acquisition, project registry reconciliation, and public index generation.
- `stage-2-sync/` owns remote change detection, source synchronization, metadata refresh, and project-state validation.
- `maintenance/` contains explicit historical migrations that do not run as part of steady-state synchronization.

External inventory snapshots belong under `data/`; Apps Script project state belongs under `projects/`; GitHub Pages projections belong under `docs/`.

GitHub Actions orchestration lives under `.github/workflows/` and calls these modules rather than duplicating their business logic.
