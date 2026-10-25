# Local engineering evidence contract

## 0.15 diagnostic evidence and storage

Crew campaign4 adds bounded initial/final contract mismatch codes, application-owned JSON schema paths/types/static hints, and up to16correlated completed native calls with safe field types/validation locations/schema digests. No artifact values, arbitrary unexpected keys, raw parser exceptions or raw model reasoning are added. Capture source is explicit for legacy schema fallback.

Measurement reports retain the full synthetic crew-measurement-1 definition and SHA256, actual budget/arm/repetition per row, manifest integrity status and unknown-aware repeated summaries. A separate private configuration fingerprint gates comparison; model/endpoint details do not appear in ZIP exports. The app-owned synthetic definition can be exported when it matches the current manifest. Raw private task/source content remains excluded. Missing observations are not zero usage or known failures.

Campaign storage accepts at most66rows/3,000,000rawUTF8bytes. Above1,000,000bytes it uses a lossless zlib/base64 envelope capped at1,000,000storedbytes with length/hash/stream/expansion checks. Smaller and legacy reports remain ordinary JSON; other report kinds stay250,000bytes. Existing global retention applies to actual stored bytes. Schema remains5; newly compressed payloads require0.15+ and downgrade reading is unsupported. Reviewed ZIPs allow at most3,000,000compressed and8,000,000uncompressedbytes with immutable approval/static names/hashmanifest. No automatic upload.


The goal is to turn operational evidence into testable changes. Collection alone does not improve model intelligence or prove product quality.

## Identities and relationships

Each session has a UUID, UTC timestamps, root workspace, immutable agent-definition snapshot/revision, parent conversation ID, capture mode, runtime state and outcome. Each event has an independent UUID, monotonically ordered local sequence, session ID, timestamp, kind, JSON payload and application version. Model request IDs connect request/response records; execution IDs connect tool requests, permission decisions and results. Tool-call IDs from models are retained separately and need not be globally unique.

`runtime.environment` records Python version, OS family, architecture and event/tool schema versions. Provider profiles and exact model names are attached to model observations. No hostname, machine identifier, GPU serial number or external telemetry endpoint is collected.

## Records

| Category | Evidence |
| --- | --- |
| Configuration | Agent saves/revisions/deletions, profile saves, retention changes |
| Task/session | Start, task length/fingerprint, parent, duration, final state |
| Provider/model | Capability evidence/source, requested profile/model, response latency, usage as reported, errors, fallback |
| Tool | Name, argument keys/fingerprint, execution/request/call IDs, actual result fingerprint, status, error/type, duration |
| File write | Verified SHA256, byte count, verification flag; full diff/content only in live review or optional transcript |
| Command | Actual exit code, stop reason, duration; full argv/output only in live view or optional transcript |
| Permissions | Requested operation fingerprint, execution ID, explicit allow/deny |
| User assessment | `goal_met` or `needs_work`, source `user`, optional redacted note, timestamp |

Runtime states: `running`, `completed`, `failed`, `cancelled`, `timed_out`, `limit_reached`, `interrupted`. `completed` means the model ended its turn within the runtime protocol. A session can be `completed` after a denied write or failed test. Tool success, command exit and human assessment must be examined separately.

Session export format v1 includes the session snapshot, ordered events, optional redacted messages and current user assessment. SQLite `user_version` manages migrations independently from agent schema v1 and event schema v1. The v1→v2 migration adds assessments; automated tests verify that old events survive.

## Privacy and storage

- Metadata mode does not persist task text, model replies, file content, command argv or command output. Workspace paths, agent instructions/configuration and error strings are still potentially sensitive metadata. A fingerprint is not encryption or anonymization.
- Session-content capture is explicit. It stores the normalized conversation, including tool arguments/results, enabling restart/resume and more detailed diagnosis. Loaded keys and recognized secret patterns are redacted recursively before serialization so JSON remains valid.
- Redaction is defense in depth, not a complete secret detector. Unknown credentials or sensitive prose can remain. Never use prompts/agent instructions as secret storage. Credential values are supplied only in HTTP authorization headers to the selected profile; `.env` files are excluded from file tools. Loading .env does not inject values into subprocess environments.
- The vault's security depends on the OS and configured keyring backend. The application does not implement a plaintext fallback. The SQLite database itself is not encrypted; it uses the user's normal filesystem permissions.
- Retention defaults to 30 days and 20,000 events. Pruning runs at startup, after runs and on request. Old completed sessions are deleted as units, configuration events are bounded, active sessions are protected, and the database is compacted. Events are limited to 32,000 serialized characters; individual file reads and writes to 100 KB, tool results to existing tool bounds, model HTTP responses to 2 MB. Agent runtime/context limits bound individual sessions. There is no hard global disk-byte quota.
- Agent revisions retain the most recent 100 per saved agent; session snapshots preserve definitions used for retained runs. Deleting an agent removes library revisions but retains historical session snapshots. Session deletion cascades messages, events and assessment. Existing exports/backups remain outside the app's control.
- Up to eight recent live conversations remain in memory for ordinary follow-up messages. Restart-resume needs opt-in content capture. Resume restores conversational text with current agent configuration; it does not rerun old tools or preserve tool-loop state.

## How to use the evidence for improvement

1. Reproduce a failure on a disposable, version-controlled fixture. Save relevant session content only with permission to retain that project code.
2. Record a user assessment and export a redacted evidence bundle. Inspect it before sharing.
3. Turn the failure into a deterministic regression case using a controlled provider response or optional real-provider integration.
4. Implement a focused change, run the existing regression cases, and compare tool outcomes, latency, usage and human assessments under the same task/model configuration.
5. Promote a verified change through ordinary source control and releases. Automatic prompt mutation, autonomous patching, remote analytics and PULSE are not implemented.

Current summaries are descriptive counts and sums. They are not statistically controlled experiments, cost estimates, automatic failure clustering or quality scores. Per-provider usage units must not be combined blindly. Ollama token counters and duration nanoseconds are labeled as received.


## 0.2.0 setup and update evidence

`setup.discovery_completed` records counts of installed models, candidate Desktop key files, loaded variables, provider IDs added, duration and exception types. Neither .env values/content nor Desktop paths are put into the event. Manual key-file loading records counts and source only. The presence/identity of a provider profile can still be inferred from local configuration.

Update events record startup/manual check outcomes, available/running versions, requested/downloaded byte counts, verification SHA-256, backup occurrence and the version observed after an installer handoff. No provider credentials, transcripts or project files are included in update HTTP. Settings can disable automatic Ollama discovery, automatic Desktop key loading, startup update checks, or the additional setup/update diagnostics. Runtime/session evidence remains a separate feature with existing retention controls.

Three local pre-update SQLite backups are kept. They can contain older retained session content; deleting a session from the live database does not scrub those backups. See INSTALLER.md. Updates are integrity-checked against the trusted GitHub release channel, not independently publisher-signed.


## 0.3 diagnostic/evaluation lifecycle

SQLite schema v3 adds a diagnostic report table while retaining existing sessions, definitions, events and assessments. Reports have independent IDs, schema/suite/app versions and per-check acceptance statuses. Local retention uses the configured age limit and a cap of 20 completed reports; interrupted checks are not relabeled successful. Exported files, GitHub issues and older backups have separate retention lifecycles.

Only the report builder's allowlisted metadata is eligible for sharing. No source tree, session transcript, task text, prompt hash, workspace path, agent name or raw exception body is included automatically. Local counts can detect the known text-tool shape in existing opt-in transcripts without sharing that content. Model names are an explicit sharing option. Public issue submission requires approval of the exact preview; edits revoke that approval.

Sharing states are `local`, `draft_opened`, `submitted` and `unknown`. A draft is not proof of upload. Ambiguous issue-creation requests are never retried automatically. Code changes, diagnostic reports and versioned installers remain separate. See DIAGNOSTICS.md and RESEARCH.md for implementation rationale and user controls.


## 0.4.0 catalogs and retention controls

SQLite schema v4 adds `model_catalogs` without replacing existing agents, settings, sessions, messages, reports or sharing states. A successful explicit model-list check stores bounded identifiers, fetched UTC timestamp, partial-page flag and a connection fingerprint (adapter/base URL/credential reference; no secret value). Failures do not replace the prior successful list. IDs are local and not automatically included in support reports. Startup restores valid retained lists without cloud calls.

**Local data** provides counts, disk usage, the actual data-folder location, catalog clearing and retention controls. Defaults: 30 days, 20 completed diagnostic/API reports, 10 MB combined report-payload/catalog budget, 20,000 session/configuration events. Report count ranges 5–200, payload budget 1–100 MB. Oldest completed records/catalogs are pruned to fit; active sessions/reports are protected and may temporarily exceed limits. The report budget is not a total database/disk cap; definitions, revisions, opt-in messages, installers and backups are separate. Each report remains bounded at 250 KB; catalog API responses at 2 MB and 5,000 IDs.

Pre-update backups now obey the same age setting as well as the newest-three cap. A live deletion does not selectively scrub unexpired backups. Exported files and public issues remain outside local retention. No automatic telemetry server or silent report upload was added. Template hashes and structural synthetic-test traces provide evidence without full template, prompt or model-text retention.


## 0.5.0 projects, retrieval and model probes

Schema 5 adds up to 100 remembered project definitions (canonical local path, name, brief capped at 4000 characters, UTC timestamps). These are configuration like agent definitions: they remain until forgotten or displaced by the 100-project cap, not the diagnostic age limit. Forget removes metadata/brief only; source files and retained sessions remain. Original Desktop keys and OS application-data locations are unchanged.

Source maps/excerpts are read on demand with no embedding request or persistent content index. Explicitly adding excerpts to a task rechecks current ignores, path protections and full-file SHA256; that task then follows existing optional transcript retention. Project briefs are user-written task instructions, not automatically harvested source. Model-generated project content remains untrusted data.

Tool-probe reports share the bounded diagnostic lifecycle: 20 completed reports / 30 days / 10 MB report+catalog payload defaults, configurable in Local data. Scoped private fields identify saved profile/model/connection/route; public reports exclude custom endpoints/profile IDs and synthetic challenge text. Model names remain opt-in. Actual dispatched generation-attempt counts are separate from metadata GETs; a request count does not certify billing or generation success. Remote probes require approval per run; no cloud probe runs at startup.

The existing /api/show request now records bounded parser, renderer and template_source strings. Native/compatible route and streaming are retained, with no raw template or model response text in support reports. No server telemetry or automatic upload was added.


## 0.6 verification and feedback

Schema5 and storage locations are retained. Python tool results add fixed status/code/line, full local revision hash and executed=false. Run summaries count historical Python passes/failures, current files needing attention, recovered stale-edit errors and unresolved tool errors. Recovery does not delete the initial failure. Human goal labels stay separate from automatic checks.

`python-static-1` selected-file reports retain local path/workspace/hash for comparison but strip them from public output. `run-review-1` reports retain a local session reference, optional model name and bounded fixed counters/check codes; no task/source/transcript/assessment note is copied. User Goal met is explicitly labeled user_goal_met, never an automatic behavior score. Recent20-run reports include fixed execution/error/assessment counters. All reports share existing retention budgets; exports/issues/backups remain separate.


## 0.7 task evidence

Schema5 and existing locations/retention are unchanged. Local events add task.context, task.checks and task.checks_evaluated; configured target paths/unmet names stay local. run.summary adds typed task-operation status/counts and final_response_status; counters distinguish actual versus unchanged writes, target mismatches and empty finals. There is no raw thinking collection or automatic extra model call. model.responded now retains actual HTTP status when available.

run-review-2 rebuilds safe task summaries from fixed enums/count keys, excluding target paths, source, tasks, agent names and assessment notes. Recent20 coverage counts which sessions recorded task checks/final status/current-version summaries, so older omissions are not treated as measured zero. Native tool/approval/stale/path guards remain; separately approved commands are not an OS sandbox.
