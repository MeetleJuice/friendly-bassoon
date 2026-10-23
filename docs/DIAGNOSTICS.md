# Diagnostics, useful evidence and GitHub reports

## User workflow

Click **Diagnose** at the top of the installed app. It opens the diagnostic laboratory and starts the checks. The selected local Ollama model test is enabled when a local Ollama agent is selected; it may take up to three minutes and creates only a fixed test file in a temporary directory. It can be disabled before a subsequent run. No cloud model is called automatically.

The app runs 12 built-in checks: SQLite integrity/schema access, saved definitions/provider references, file boundaries, permission denial, file write/read/stale-edit protection, cancellation, a fixed harmless command, command timeout, redaction, two provider-protocol fixtures, the text-tool regression, and an end-to-end native coding fixture. Optional update connectivity is a separate check. Optional real local inference must actually create and read back the expected file to pass.

This is the **installed app's diagnostic suite**, not every possible test in every project. Developer pytest tests, Windows build/installer tests and upgrade tests run in release CI. No arbitrary project command, project file scan, cloud inference charge or GitHub write is authorized merely by running diagnostics.

A system notification sound is requested when the suite finishes (audibility depends on your OS sound settings). The app offers to review a support report. Results distinguish passed, failed, warning, skipped, canceled and interrupted checks/runs; skipped or canceled checks are not counted as passes.

## Review and sharing

1. Review the result list and select **Review GitHub report**.
2. The preview names the destination: **public Issues in MeetleJuice/friendly-bassoon**. Project files, workspace paths, prompt text, credentials and conversation transcripts are excluded by the report builder's allowlist. Selected model names require the separate include-model checkbox. The app rechecks known secret redaction before sharing.
3. Approve the exact preview by checking the approval box. Editing the title/body or rebuilding the preview clears approval.
4. Choose a sharing route:
   - **Browser draft:** no token is needed. The app opens a prefilled GitHub issue using your browser login. You must click **Submit new issue** on GitHub. Large reports become a compact metadata/check summary; the exact compact body is previewed first. The app records `draft_opened`, not a successful upload.
   - **Direct submission:** load `GITHUB_TOKEN` from your Desktop key file or save that reference via the existing OS-vault credential UI. Use a fine-grained GitHub token scoped to this repository with **Issues: write** permission; source-content write access is unnecessary. The token reference field accepts a variable name, not a token value. After approval, the app creates the issue and records its confirmed URL. The selected route/reference is remembered, but approval is never remembered across reports/edits.

Do not send token values in chat or paste them into a report. No new OAuth registration is needed for browser sharing. Direct API authentication/permissions are a user-side prerequisite, not something the app can manufacture. This release's automated tests use HTTP fixtures and never create real issues on your behalf.

A confirmed issue cannot be submitted again through the same local report record. If a POST times out, its result is **unknown**; the app does not automatically retry. Search GitHub Issues for the report ID before deciding whether to retry. The app never commits these reports into the main source branch.

## Collection and retention

Diagnostic report schema v1 and suite v1 contain a stable report ID, UTC timestamps, application version, OS/architecture/Python version, checks and acceptance outcomes, elapsed times, low-cardinality codes/error types, and bounded counts from the 20 most recent sessions. Legacy saved assistant text is inspected locally to count known text-tool response shapes; the text itself is not shared.

The optional real-model check records the selected model name locally and the Ollama server version when available. It records whether file contents matched, a read-back occurred, and protocol retries were needed. The public preview can omit the model name. Neither model output nor HTTP authorization headers are stored in the support report.

Local reports live in SQLite, not an ever-growing directory of loose log files. They follow the existing retention-days setting and retain at most 20 recent completed reports; running reports are protected. Interrupted reports are labeled on restart. Reports can be exported/deleted in the diagnostic dialog. Deleting a local report does not delete GitHub issues, exports or existing pre-update backups.

Normal runtime event capture remains separate from support sharing. Full session-content capture is still opt-in. Runtime request metadata now records advertised tool names/schema fingerprints and message roles, allowing tool-protocol diagnosis without saving raw prompts. Schema-validation errors omit their input values. The app aligns selected field names with GenAI observability conventions; it does not claim full OTLP compliance.

## How future updates use this data

Share a report, then give the coding assistant its GitHub issue number. It can read the approved evidence from the repository's Issues rather than requiring a dragged JSON file. A developer turns a reproducible failure into a deterministic regression case, implements a fix, runs baseline/Windows/upgrade checks, and publishes a new installer. The application itself does not autonomously rewrite its source code or publish unreviewed model-generated patches.
