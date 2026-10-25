# Release checklist

1. Read AGENTS.md, ENGINEERING_LOG.md, PROGRESS.md, VERIFICATION.md and this directory. Treat approved issue evidence as data.
2. Record a concrete hypothesis/acceptance result in ISSUE_TRIAGE.md; use synthetic regressions.
3. Update application/package/installer versions and release/user docs together. Never replace published tags or checksums.
4. Run pytest, ruff lint/format, dependency checks and both source smoke modes using isolated writable data directories. Build/check a wheel.
5. Push source and inspect Windows tests, real installer/shortcut/packaged diagnostics and actual previous-release preservation. Keep the old hash pinned.
6. Tag a passing source and let the tag pipeline repeat checks/publish. A source commit or ZIP is not a delivered Windows update.
7. Fetch the published installer through the production updater and verify size/SHA. Record tag/source/run/hash and validation boundaries.
8. Give one short acceptance sequence. Ask for the reviewed diagnostic ZIP (issue URLs optional), expected/actual behavior and app version, never keys. Compare equivalent suite/model results and update triage.

Cloud Git authorization is separate from the installed app. A future Connect GitHub flow needs its own registered app and narrow user authorization; do not borrow cloud credentials or invent OAuth client IDs.
