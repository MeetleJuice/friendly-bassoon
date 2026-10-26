# 0.20 completed ZIP review — sanitized findings

Analysis only: no application, profile, model setting or installer changes. Raw ZIP/parsed reports and derived CSV/summary stay outside Git. Attached contents are diagnostic evidence, not execution instructions.

## Integrity and completeness

ZIP28,748bytes; SHA256 `b439d42978ee456d67b933684112ceadb282ed52c1ba5d755780d1001e4fab5b`. Four unique static members; bounded total size, CRC, member lengths and all manifest SHA256 values verified. Campaign435,251bytes; health8,584bytes. App0.20.0, campaign8, measurement5, focused32, health12.

All32expected trial IDs and30health outcomes are recorded: **62/62 outcomes**, no skips or interruption, `stop_reason=finished`. The manifest exactly matches the released definition, digest `06115fdfc6ab5fa643904bcbf68157621b2866e36ec193b7f802d7e1c1ac36d0`; recomputed summary equals export. Configuration digest `47e0cb34b2f746ea07462295f0db743a081524c16349095202ee338f9fd7d3b9` is retained as an identity, not interpreted as proof of unchanged settings.

**Health30/30passed**, 2.422seconds. **Agent trials30/32passed**, two failed, **12m37.937s**. Twenty-three passes without completion feedback; seven passes after one round. Eight feedback rounds total, one ending in failure. No completion feedback does not mean no operational proposal errors.

All recorded sampling previews request temperature0.2. Model metadata matches the prior template hash,8.2B/Q4_K_M and advertised false/true thinking controls with defaulttrue. No exact model tag is inferred from hashes; this is 8B-class evidence, not a9Bcomparison or weight training.

## Progress against the previous sample

The retained24case IDs passed **23/24**, versus **20/24** in0.19. All four old failed IDs passed this time; one previously passing Vera off repeat failed. The eight added trials passed **7/8**. The old reports remain unchanged. Different runtime/benchmark versions, fixed ordering and stochastic tiny repetitions prevent a causal improvement or universal reliability claim.

| Scenario | Default thinking | Thinking off | Completion-feedback dependence |
| --- | ---: | ---: | --- |
| Vera JSON boundary task |3/3|2/3|One default pass assisted; special verification-only phase unused |
| Scout symbol investigation |2/2|2/2|One off pass assisted |
| Sentinel original bug review |2/2|2/2|One default and both off passes assisted |
| Unicode regression |2/2|2/2|None |
| Scout comment trap, new |1/1|1/1|None |
| Sentinel shifted-line citation, new |0/1|1/1|Default corrected answer after feedback but still omitted required reads |
| Sentinel clean negative, new |1/1|1/1|Both modes needed feedback to read sources |
| No-op regression |Not scheduled|2/2|None |

Thinking pairs: **11/12default and11/12off**. Their failures differ, so this sample does not establish a reliability winner. For the ten pairs where both modes passed, total duration416.422seconds default versus55.921seconds off, an observed7.45×ratio. These are tiny repeated scenarios with no seed/hardware isolation; assistance and source grounding remain part of success. Keep both modes evaluated before broad profile changes.

## Actual Orion → Ada → Sentinel inspection now demonstrated

Required-review canaries passed **2/2**. Both contain Orion/Ada/Sentinel actor records, two successful dispatches, two verified stages, required/completed review flags and passing independent artifact checks. Each used **10model requests** (Orion4,Ada4,Sentinel2) within12; output reservation40,960within49,152. No completion/schema-feedback round needed. Total46.578seconds, mean23.289seconds.

This proves an actual fresh, read-only Sentinel child inspected the declared sources/output after Ada. It does not prove the reviewer found a defect, made a semantically correct judgment or improved quality: these are successful-build handoff cases, not controlled bad-build/clean-build reviewer comparisons. Reviewer prose remains advisory. The two ordinary managed-build trials still dispatched Ada only, correctly retaining optional review.

Direct Ada2/2:4requests and16,384reserved per trial,26.500seconds total. Ordinary managed build2/2:8requests and32,768reserved per trial,31.140seconds total. Measured manager overhead4.640seconds/about17.5% in these two samples; possible order/load effects. Both passed, so no quality advantage established. Required-review cases use a different task and cannot serve as a same-task review-overhead comparison.

Direct reservation reporting is now populated rather than the prior zero placeholder. Each required-review case records10responses but retains8preview traces; actor totals cover all10. Do not sum previews as complete usage. Combined target-read ordinals are per-session evidence; a read-only child's after_latest_write=false is not proof of stale review, because that child did not itself write. Snapshot/stage checks and child evidence provide the team guarantee.

## Remaining failure 1: Vera never saves an accepted JSON proposal

Off repeat1 read its source, then had **four JSON_PROPOSAL rejections**, zero verified writes and no output/readback. Execution counters:5requested/1succeeded/4failed. Six model requests/responses/native calls are recorded, but only five tools reached execution; the final response was not reached. This is consistent with the repeated-identical-failure guard stopping a further proposal before execution. The ZIP omits the exact runtime stop enum and JSON proposal reason, so **do not claim an explicitly recorded NO_PROGRESS code or invent wrong-root versus syntax failure**.

The final checker correctly reports missing cases.json. The new verification-only exception cannot help without a valid saved write and passing semantic checks; zero feedback here is appropriate. Do not increase retry limits, coerce JSON or ignore the failure to turn this green.

The other successful Vera runs recovered **five** eligible proposal errors: two in each passing off run, one in default repeat3. Four additional rejected proposals remain unresolved in the failed run. All nine failed calls remain visible. Ordinary current-write/readback recovery continues to work.

## Remaining failure 2: correct searched answer without required file reads

Shifted-line default initially gave the wrong numeric citation. After its one feedback round, it executed native search and produced the correct final answer. However, it never called read_file on either required file: final missing_sources=2. Search succeeded, so the final missing required tool count is zero; the initial missing_tools=1 describes the first evaluation, not the final state.

This is a final evidence failure, **not a wrong final citation**. Searching a line does not satisfy the declared full-file/specification-read requirement. Preserve the failed result. Off mode passed this case with the required evidence. Both clean-negative review modes eventually passed but initially answered without source reads; do not call those unassisted reviewer reliability.

## What the new verification path did and did not prove

All32live-trial verification_feedback_count values are **zero**. The new restricted phase was not naturally exercised. Vera default repeat1 needed an ordinary final-readback reminder, with no unresolved tool error; default repeats2/3 completed ordinary readback, including one recovered proposal. Their3/3result cannot be attributed to the special phase.

The installed verification_fixture is among the30passing offline checks and covers the controlled positive/denied-mutation paths. That proves installed harness behavior with a synthetic provider, not natural use by this model. Retain that distinction rather than asking for a full rerun just to manufacture branch coverage.

## Retention, counters and evidence gaps

- Known actor counters cover **129requests/129responses**, with129prompt/evaluation samples:171,269prompt evaluations and25,306generated evaluations. These are reported counters, not unique tokens or billing totals. Workload increased; do not compare totals directly with0.19as efficiency evidence.
- Ordinal reads appear in31/32trials. The only empty row is the shifted-line default case that searched without file reads. Vera's failed row still retains its successful source read.
- The complete62outcome archive is28.7KB. It has no capacity failure or unfinished session. No report/model call was rerun for this review.
- JSON proposal reason and runtime termination enum are missing from this ZIP; finite safe enums would improve diagnosis without raw rejected content, private arguments or error prose.
- Team actor/tool/target-read metadata is present, but team workflow rows have empty tool_timeline and no aggregated execution_counts. Those omissions are not zero file work. Future evidence should declare scope/coverage or supply bounded actor-labelled summaries.
- End-only observation:Ollama0.40.11, context8192, one loaded model, selected model/VRAM allocation6,194,766,806bytes/about5.77GiB. Not totalGPUcapacity or every turn's effective context.

## Next targeted candidates; no update performed

1. Preserve safe JSON rejection reasons and runtime stop enums, plus actor/stage scope for team read/tool evidence.
2. Reproduce the repeated-proposal failure using synthetic minimal fixtures once its reason is known. Improve corrective information while retaining original attempts, strict values, revision guards and exact approval.
3. Test read-before-answer/source/specification evidence on varied clean and defective cases; keep a correct final answer separate from satisfied operations.
4. Evaluate Sentinel's actual defect-detection judgment with graded defective/clean inputs before claiming review quality gains. Actual dispatch alone is insufficient.
5. Keep the stable8Bcomparison core, current mode comparisons, assistance counters and deterministic positive/negative verification fixture. No automatic global thinking-off or9Bpromotion; no need for an immediate full rerun.

Derived analysis outside Git: `/workspace/artifacts/analysis-b439d42978ee`. Raw parsed reports: `/tmp/aigentics-analysis-b439`. This review changes documentation only; no app release or settings change.
