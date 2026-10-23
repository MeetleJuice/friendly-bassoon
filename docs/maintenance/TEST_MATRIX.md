# Test matrix

| Layer | Location | Acceptance | Limits |
| --- | --- | --- | --- |
| Unit/regressions | Linux and Windows CI | Temporary filesystem/process operations, controlled provider HTTP, permissions, protocol, catalogs/retention and UI workers | Fixtures are not live models |
| Packaged diagnostics, suite 2 | Source and installed app | 14 disposable checks including GET-only catalog/deduplication and active-report retention | No user project testing or automatic cloud generation |
| API models, api-models-1 | Explicit Test APIs action | At most one GET per unique adapter/endpoint/credential reference; parsed, cached, dated models | First page only; no generation/tool/billing certification |
| Optional real local model | User's PC | Exact disposable file bytes plus read-back and completed runtime | Up to 180 seconds of local generation; no cloud fallback |
| Fresh installation | Windows CI | Real installer, shortcut, executable startup, installed diagnostics | Not the user's GPU/Windows 10 |
| Upgrade from 0.3.0 | Windows CI | Pinned old installer SHA; agent, setting, session, message and diagnostic sharing state survive schema 3→4 | No backward downgrade support |
| Published download | Cloud | Production updater checks actual release size/SHA | Same GitHub trust channel; unsigned exe |
| Report sharing | Fixtures/user browser | Exact preview, model opt-in, redaction, approval; draft distinguished from upload | No live issue creation in automated tests |

Run AGENTS.md's checks and record actual counts/run IDs in ENGINEERING_LOG.md and VERIFICATION.md. Keys stay on the user's PC. Prefer one focused acceptance run per meaningful change over repeated tests of every model.

Validated 0.4.0 baseline: 107 passed, 1 live-Ollama skipped; Windows source run 39987348899 and tag/release run 39987814325 passed. The actual released installer download/checksum passed; see VERIFICATION.md.
