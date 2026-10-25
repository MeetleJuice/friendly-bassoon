# 0.19 completed ZIP review — sanitized findings

Analysis only. Application code, agent profiles, model settings and installers are unchanged. Raw uploads and parsed reports remain outside Git. This review records observed results rather than regrading historical runs.

## Integrity and completeness

- ZIP: 24,041 bytes; SHA256 `6a5b7a5aab4e52f1f5f536eb7cc4d99f326616956ee2284e2bd7267b20ec2fe3`.
- Four unique static members; CRC, member lengths and all manifest hashes verified. Campaign JSON is 320,478 bytes; health JSON is 8,297 bytes.
- Exporter/application: 0.19.0. Campaign: crew-campaign-7, focused mode, `stop_reason=finished`.
- All 24 planned trial IDs recorded; no missing, skipped or interrupted cases. Health records all 29 checks: 53 recorded outcomes overall.
- Measurement manifest exactly matches the shipped definition, digest `158ad54343cc8565ca22544d71487a636281c2824c0a6efe8d322dc57e15068e`. Recomputed repeated summary equals the export.
- Configuration digest: `005710317b014d5b75bb92a3fff3e54d46e6152b70a7107bf1f875ef82409504`.

Health: **29/29 passed**, 2.312 seconds. Agent trials: **20/24 passed**, four failed; campaign duration **9m41.703s**. Eighteen passes needed no completion-feedback round; two passed after one round. Two other feedback rounds ended in failure. Absence of completion feedback does not mean absence of tool errors or recovery.

All trial metadata reports 8.2B / Q4_K_M and explicit thinking support for false/true, with default true. Exact model names are deliberately omitted; do not infer a tag from hashes. These are current 8B-class observations, not evidence about the proposed 9B model.

## Results by scenario

| Scenario | Default thinking | Thinking off | Default total seconds | Off total seconds |
| --- | ---: | ---: | ---: | ---: |
| Vera: exclusive-boundary JSON task | 1/3 | 3/3 | 182.735 | 35.110 |
| Scout: symbol investigation | 1/2 | 2/2 | 57.656 | 6.157 |
| Sentinel: bug review | 1/2 | 2/2 | 120.234 | 8.171 |
| Unicode regression | 2/2 | 2/2 | 89.922 | 8.109 |
| No-op regression | Not scheduled | 2/2 | — | 10.891 |

Workflow trials use thinking off in both arms: direct Ada **2/2**, 25.515 seconds; managed Orion **2/2**, 32.906 seconds. This focused suite does not independently evaluate all six crew members or their broader skills.

Nine eligible same-task thinking pairs: default **5/9**, off **9/9**. Five pairs passed in both modes: their total durations were 203.078 seconds default versus 26.813 seconds off, an observed 7.57× ratio. Do not count failed work as successful speedup. All four failures were in default-thinking trials; all 15 thinking-off trials, including workflow and unmatched no-op cases, passed.

This is a small repeated sample, with fixed ordering and no seed or hardware isolation. Sentinel's two off passes still required completion feedback. It supports further scoped off-mode evaluation, not a universal reliability claim, global default change or model training claim. The shorter focused run and previous 56-trial full run have different workloads; their wall-clock difference is not an agent speedup measurement.

## Orion now dispatches successfully; reviewer stage remains untested

Both managed trials dispatched Ada once, verified the build stage and passed independent output checks. Actor statistics contain Orion and Ada only. Manager diagnostics record successful `team_status`, `dispatch_worker` and `inspect_evidence`; no schema correction was needed. Merely entering the review stage does not mean Sentinel ran: **neither trial dispatched Sentinel**.

Compared with 0.18's two pre-dispatch failures, this is concrete progress in delegation. The old export omitted the rejection reason, so these successes do not establish the exact old failure cause.

Each managed trial used eight model requests: four Orion plus four Ada. Direct Ada used four requests per trial, under the same shared 12-request ceiling. Managed time was 7.391 seconds higher overall, about 29%, with only two samples and possible loading/order effects. Both approaches passed; these cases establish working dispatch, not a demonstrated quality advantage from management or independent review.

Known response usage: direct prompt/evaluation counts 11,908/600; managed 19,655/932. Managed output reservation was 32,768 per trial under a 49,152 ceiling. **Direct `output_reserved=0` is an instrumentation gap, not zero output or a free run**: team_evaluation constructs a direct RootBudget without retaining its summary, then substitutes zero for absent budget data. Its nonzero actor evaluation counts remain available. Fix budget reporting before comparing reservation efficiency.

## Vera's proposal recovery works; final-read recovery has a gap

All three off-mode runs encountered rejected JSON proposals: one, two and one `JsonProposalError` events respectively. Each then made a permitted verified write, read the current output revision and passed strict content/operational checks. The four failed calls remain visible. This is live evidence of the intended proposal-correction path, rather than a clean first-write success or weakened grading. No completion-feedback round was used in these three runs.

Default repeat 1 passed. Default repeats 2 and 3 each omitted required `expected_sha256` on an initial write, corrected the call and saved content that passed the semantic checks, but **never read the final output back**. Both correctly remain `needs_review`, with TASK_VERIFIED and RUN_COMPLETED false. Their missing current readback also prevents the earlier eligible proposal error from resolving.

Source inspection explains the zero completion-feedback count: proposal recovery requires verified write plus current readback, while the completion-feedback gate requires zero unresolved errors. The final-read omission can therefore leave the run unable to receive that reminder. A future correction should consider narrowly bounded verification-only feedback for eligible no-effect proposal errors after a valid write. Preserve current-revision proof, original failed counters, denial handling, deadlines and strict acceptance; never auto-read or silently forgive an unresolved action to manufacture a pass.

## Other two failures

- **Scout default repeat 2:** final answer met content checks, but both responses used no native tools. Neither required source was read, including after the single feedback round. A plausible correct answer does not satisfy evidence requirements.
- **Sentinel default repeat 2:** required sources were eventually read, but `/findings/0/line` remained the wrong numeric value after feedback. The export identifies the field and types, not the actual values. Do not invent an off-by-one explanation. This is a remaining semantic citation failure.

Across the campaign, six failed file-tool calls are retained: four JSON proposal rejections in successful Vera off runs and two missing-argument rejections in failed Vera default runs. All four trial failures must stay recorded.

## Diagnostic retention and evidence quality

Ordinal target-read evidence is populated in **23/24 trials**, including source reads and post-write output reads on Windows. The sole empty case is Scout's observed no-tool failure. This supports the Windows path-normalization correction; the 0.18 blanket-empty arrays were an emitter defect, not proof that those historical agents never read files.

Actor totals cover 89 requests and 89 responses: known prompt evaluations 116,979; known generated evaluations 19,632. These are server-reported counters, not billing totals or unique prompt tokens. Actor totals and bounded request previews serve different purposes; do not sum truncated previews as if complete or treat the direct reservation placeholder as measured usage.

End-only server observation reports Ollama 0.40.11, context 8192, one loaded model and selected allocation 6,194,766,806 bytes, including reported VRAM allocation of the same size (about 5.77 GiB). This is not total GPU capacity or proof of every turn's effective context.

The complete campaign and health evidence survived storage/export in a compact ZIP. No GitHub issue, generation API key check, automatic upload or new model call was needed for this review. Raw data stays outside Git; only these sanitized findings are committed.

## Proposed next targets

1. Reproduce the Vera valid-write/missing-readback feedback dead end with a synthetic fixture, then design the narrow verification recovery described above.
2. Make Sentinel line citations mechanically checkable and expand Scout source-grounding cases. Retain wrong-answer and missing-evidence failures as separate categories.
3. Add a controlled case that actually requires a Sentinel child review after Ada, including rejection/repair and shared-budget checks. Do not force a reviewer into every ordinary task merely to increase counts.
4. Report direct and managed budgets consistently; preserve actor totals, trace coverage and unknown/missing distinctions.
5. Retain a small comparable core and add varied boundary/negative cases. Keep the current 8B engine stable for that experiment; any 9B comparison needs separate matched runs.

No immediate repeat is needed: this completed ZIP is sufficient for the next targeted update plan. These are analysis recommendations, not an app implementation or release. Derived summary/CSV are outside Git in `/workspace/artifacts/analysis-6a5b7a5aab4e`.
