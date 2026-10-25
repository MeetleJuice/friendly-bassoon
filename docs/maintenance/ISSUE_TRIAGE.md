# Current issue triage

## Confirmed baseline, 2026-10-23

Approved reports: [#1](https://github.com/MeetleJuice/friendly-bassoon/issues/1), [#2](https://github.com/MeetleJuice/friendly-bassoon/issues/2). Both use app 0.3.0, suite 1, Windows 10, and a server reporting Ollama 0.40.8.

| Model | Local-model test | Duration | File/read-back | Other checks |
| --- | --- | --- | --- | --- |
| qwen2.5-coder:7b | protocol_error after 2 corrections | 10,328 ms | neither verified | 13 passed |
| qwen2.5-coder:14b | protocol_error after 2 corrections | 43,500 ms | neither verified | 13 passed |

Changing size within this family did not resolve the failure. The reports do not prove the model, template, server or adapter is solely responsible. Passing controlled fixtures does not establish live compatibility.

## Next useful evidence

Suite 2 records bounded per-request structure, advertised tool count/schema fingerprint, native call count, text-tool detection, generation counters, finish reason, capability source and template hash/length/tool-marker presence. No template contents, prompts or model text are retained in the report. Compare the same model before/after; do not request repeated identical runs until a hypothesis changes.

API listing is a separate suite (`api-models-1`): a valid first-page metadata response does not certify generation permission, quota, billing status or native tools. Public endpoints may respond even with an invalid credential. Pagination, empty lists, missing keys, HTTP status and cancellation are explicit.

## Follow-up order

1. Obtain one suite-2 local-model report and one API-check report after 0.4.0 installation.
2. Inspect native-call presence, template fingerprint and metadata consistency against the official protocol using synthetic requests.
3. Add a minimal regression before changing adapter behavior. Preserve native tools, validation and approval.
4. Repeat a live test only after a meaningful change. A different model family is a comparison, not proof of a repaired integration.
5. Track GitHub account connection, provider forms and model capability certification as future work. Listing a model must never label it a proven coding model.

0.4.0 is published and its installer verified. Awaiting the first user API-check and suite-2 local-model reports; do not infer their outcomes from the release pipeline.


## 0.4.0 acceptance received

Report #3 confirms 15 checks passed and the actual Qwen14b workflow failed. All three responses lacked native tool_calls, were detected as text-tool output and ended with stop, not reported truncation. /api/show declared tools and a 1615-character template with tools markers. This still does not identify the active parser.

Report #4 confirms five metadata endpoints passed in 1000 ms: Gemini 60, Groq 11, NVIDIA 85, Ollama 8, OpenRouter 468. One GET per provider, no generation requests; no generation/tool certification is inferred. HTTP-success status/environment were missing, recent counter defaults had wrong types, and four failed sessions lacked useful classifications; 0.5 addresses those report gaps.

The targeted next result is a 0.5 native-call probe (optionally four local routes), plus parser/renderer/template_source in a full suite-3 report. Same model/connection scope is required for retained probe comparisons. No current evidence establishes a repaired live Qwen integration.

## 0.5 live acceptance and 0.6 priorities

Approved issues #5–#8 were read. #5: four Qwen14b route/stream probes all HTTP200, TEXT_TOOL_RESPONSE, zero native calls. #6/#8:17 offline+update checks pass; Qwen14b file test protocol_error, go_template; no file/read-back. #7:five model-list checks pass in969ms, one GET each, zero generation; OpenRouter469, Ollama8, Gemini60, Groq11, NVIDIA85.

The supplied Qwen3:8b session proves native approved file writes/read-back work on the user's installation. It also exposes repeated wrong/stale revision tokens, recovered edits marked needs_review, literal tuple assignment failure, missing runtime verification and confused planning/identity context. No captured launch or final pure-code music result exists. Do not commit the original log/source. 0.6 targets evidence/checks/recovery UX, not a fabricated Qwen2.5 repair. Next useful acceptance: one fresh Qwen3:8b Python edit and its run review, plus actual user gameplay result.


## 0.6 acceptance and 0.7 targets

Issues9–12 reviewed:9 repeats old Qwen14b failure;10 passes all21 health checks including live local exact file/read-back;11 catches syntax error line1;12 has7successful tools/one static-checked write but Needs work. The pasted corresponding log confirms wrong output filename and a redundant existing-file rewrite. Supplied Qwen3.5 logs show11successful tools but3empty final answers; no raw server cause established. Captured source hashes confirm literal newline escapes in some earlier Python files. Do not commit original traces/source or infer all reports share the same model/version.

0.7 verifies explicit operations, blocks wrong file-tool targets, preserves incomplete-response work, defaults to actual fresh context and records safe evidence coverage. Generic prose truthfulness, Qwen2.5 repair and gameplay remain unproven. Next acceptance: one fresh simple targeted write plus post-write read-back and actual user assessment; do not repeat unchanged Qwen14b comparisons.


## Issues24/25 → 0.14

31/42live attempts pass,24/24offline pass. See UPGRADE_0140_PLAN.md for the full failure classification and caveats. Prioritize content correctness inside bounded feedback, pre-tool output-limit shape, misleading-source variants and group-separated comparisons. Do not infer exact wrong bytes/answers from the public flags; raw synthetic outputs are not in these reports.


## Approved ZIP ea5d5fe33596 — 0.15 response

Full manifest hashes validated.66 campaign rows=36passed,28evaluatedfailures,2unknown; health25/25. Rich exported counters expose token/time limits and verification-only repairs, but absent actual artifacts prevent semantic diagnosis. Add safe mismatch types/schema pointers and per-call argument/type/schema evidence. Freeze repeated measurement separately from discovery; do not expand scenarios and call the resulting score a controlled improvement. Synthetic contract calibration found strict formatting/key/citation ambiguity and one real numeric grader crash, now covered. Raw ZIP and transcripts remain outsideGit. See UPGRADE_0150_PLAN.md.
