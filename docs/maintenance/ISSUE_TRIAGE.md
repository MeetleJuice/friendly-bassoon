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
