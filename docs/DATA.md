# Local engineering evidence contract

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
