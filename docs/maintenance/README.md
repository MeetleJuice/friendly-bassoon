# Project maintenance workspace

Start here for the next update. This is durable engineering memory in Git; user traces and credentials belong outside the source tree.

- [0.18 Orion/calibration implementation plan](UPGRADE_0180_PLAN.md) and [latest 0.17 result review](RESULTS_0170_REVIEW.md) — delivered; [verified installer receipt](RELEASE_0180_VERIFIED.json).
- [0.17 verified completion and observable thinking](UPGRADE_0170_PLAN.md), [research](RESEARCH_0170.md) and [source hashes](RESEARCH_SOURCES_0170.json), plus the [verified delivery receipt](RELEASE_0170_VERIFIED.json).
- [0.16 Midnight Crew interface](UPGRADE_0160_PLAN.md) and [primary-source UI research](../design/UI_RESEARCH_0160.md).
- [0.15 precise diagnostics and repeated measurement](UPGRADE_0150_PLAN.md).
- [Diagnostic ZIP workflow](DIAGNOSTIC_BUNDLES_PLAN.md) — local review/export in0.14.1; direct upload remains future work.
- [0.14.1 report-capacity recovery](HOTFIX_0141.md).
- [0.14 correctness and failure-evidence plan](UPGRADE_0140_PLAN.md).
- [0.13 bounded completion plan](UPGRADE_0130_PLAN.md).
- [0.12 Midnight Crew and campaign plan](UPGRADE_0120_PLAN.md): versioned roles, individual evaluations, bounded continuation, and two reviewed reports.
- [Midnight Crew visual direction](../design/MIDNIGHT_CREW.md): supplied character-sheet reference and original-asset availability.
- [0.11 evaluation/recovery plan](UPGRADE_0110_PLAN.md) and [checkpoint audit](CHECKPOINT_0110_REVIEW.md).
- [0.10 coordinated-budget and checkpoint plan](UPGRADE_0100_PLAN.md).
- [0.9 research and implementation plan](UPGRADE_090_PLAN.md).
- [0.8 guided suite plan](UPGRADE_080_PLAN.md) and [research](RESEARCH_080.md).
- [0.7 upgrade plan](UPGRADE_070_PLAN.md) and [research](RESEARCH_070.md): explicit task checks, preserved work and fresh context.
- [0.6 upgrade plan](UPGRADE_060_PLAN.md) and [source research](RESEARCH_060.md): checks, recovery and useful run evidence.
- [0.5 upgrade plan](UPGRADE_050_PLAN.md) and [source research](RESEARCH_050.md): implementation and acceptance rationale.
- [Issue triage](ISSUE_TRIAGE.md): verified findings, evidence boundaries and the next experiment.
- [Test matrix](TEST_MATRIX.md): what each test layer proves and what needs live acceptance.
- [Release checklist](RELEASE_CHECKLIST.md): repeatable validation, upgrade and delivery.
- [User testing guide](USER_TESTING.md): help without excessive or private data.
- [Engineering log](../ENGINEERING_LOG.md): decisions, checks, release IDs and installer hashes.

```text
aigentics/             application and packaged diagnostics
tests/                 synthetic regressions; no real user exports
scripts/               build, installed-app and upgrade probes
docs/maintenance/      triage, test matrix, release and user workflow
docs/ENGINEERING_LOG.md
.github/workflows/     Windows validation and releases
```

On the user's PC, **Local data → Open local data folder** shows the actual location. `aigentics.sqlite3` stores definitions, history, reports and catalogs; `backups/` contains bounded pre-update snapshots; `updates/` holds verified installers. Installation, coding projects, the original Desktop key file and local records have separate roles. Do not move existing folders or keys to match example paths. Upgrades use the same data location.

Cloud artifacts go in `/workspace/artifacts`, outside the repository. Temporary research and isolated smoke data go in `/tmp`. Never copy a Desktop `.env`, raw support export or credentials here. Link approved issues and commit sanitized conclusions and synthetic regressions.
