# Automation

`automation/` contains **how synchronization is performed**.

The synchronization architecture separates implementation from observed data and materialized project state:

- `shared/` contains repository, OAuth, and validation primitives shared by stages.
- `stage-1-inventory/` owns Drive inventory acquisition, project registry reconciliation, and public index generation.
- `stage-2-inspection/` is the Phase 2 clasp-free Apps Script API inspection/planning implementation. It observes project/content/deployment/version state and emits a deterministic materialization plan without changing canonical project state.
- `stage-2-sync/` remains the currently orchestrated compatibility synchronization path until the three-stage workflow cutover. It still combines inspection, clasp source synchronization, metadata refresh, and project-state validation.
- `maintenance/` contains explicit historical migrations that do not run as part of steady-state synchronization.

Direct Drive and Apps Script API callers acquire bearer tokens through `shared/google_oauth.py`. This provider reads compatible clasp authorized-user credentials but does not mutate clasp's credential store; clasp commands remain responsible for their own OAuth refresh.

External inventory snapshots belong under `data/`; Apps Script project state belongs under `projects/`; GitHub Pages projections belong under `docs/`.

GitHub Actions orchestration lives under `.github/workflows/` and calls these modules rather than duplicating their business logic.

The current workflow still invokes `stage-2-sync/`. `stage-2-inspection/` is intentionally additive in this transition PR so the new inspection authority can be validated independently before Stage 3 materialization and workflow cutover.
