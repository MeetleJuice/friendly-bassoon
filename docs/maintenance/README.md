# Project maintenance workspace

Start here for the next update. This is durable engineering memory in Git; user traces and credentials belong outside the source tree.

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
