# 0.18 completed ZIP review — sanitized findings

Analysis only; no application/model/profile/installer change. Raw ZIP and parsed reports remain outside Git. User supplied the ZIP in response to the requested post-update campaign. Model name is intentionally absent; metadata explicitly reports8.2B / Q4_K_M, consistent with the current8Bclass. Exact model tag is not inferred from hashes. Last user confirmed8B; this upload contains no affirmative9Bswitch.

## Integrity and completeness

ZIP35824bytes; SHA2564bfd02982444c88377779ef4ad0fa47962a0e27d509e3e584825fcc132d5712b. Four static members, valid CRC, unique names, bounded sizes, all manifest member lengths/SHA256verified. Campaign report599141bytes; health8013bytes. All56planned trial IDs recorded, stop_reason=finished, no skips/interruptions. Manifest3equals the shipped definition, digest2e90f43b81731250ffe9d77c4a17256ebdcb45bafa6d2109c9f33f1ba8749142. Recomputed repeated summary equals export. Local configuration digest0d10f249ba06f0868f448970a4f6f62f52ce4db2a19b618ab89591eecd618b5a.

Health28/28passed. Trials40/56passed,16failed;32m11.922s.29passes without a completion-feedback round;11passes after feedback;18feedback attempts overall. First-try here means no completion-feedback round, not absence of any operational error/recovery. Tool counters across exported execution counts:146requested/137succeeded/9failed,27actual verified writes,7unchanged writes,12Python static passes,5recovered stale edits,1empty-final response. Team routing calls are separate; these file-tool counters do not cover all manager native calls. Failed tool classes5StaleFileError,3FileNotFoundError,1ValidationError.

## Controlled thinking comparison within this run

22eligible same-task/budget pairs:18rolepairs plus4Unicode/no-op pairs. Every recorded sampling trace requests temperature0.2; top-p/top-k inherited. Explicit controls report defaulttrue and supportedfalse. Default16/22passed; off19/22passed. Total pair-group time1252.889s default versus151.591s off, but this includes failed trials and is not a successful-work speed claim. For15pairs where BOTH passed,742.824s→103.531s:7.17x observed duration ratio,86.06%less time. Retained generated-token counters45102→3792; bounded traces/known counters are not complete billing totals or hidden-compute measurements. Fixed order, tiny scenario coverage, no seed/hardware isolation; do not generalize to all tasks or9B.

| Role / repeated core scenario | Default | Off | Default total seconds | Off total seconds |
| --- | ---: | ---: | ---: | ---: |
| Historical generalist George |3/3|3/3|210.093|32.703|
| Scout |3/3|3/3|54.734|17.328|
| Ada |3/3|3/3|163.921|32.453|
| Vera |1/3|0/3|247.298|30.045|
| Sentinel |1/3|3/3|139.781|12.281|
| Atlas |3/3|3/3|147.076|8.829|

Roles alone14/18default versus15/18off. All3off Scout passes and all3off Sentinel passes needed the existing feedback round to read required sources/correct the answer. These are feedback-dependent successes, not first-try reliability. Off is promising for five roles but is not a safe blanket improvement for Vera. Each role still repeats just one scenario.

Unicode:off2/2, coordinated-default2/2; reference1/2 with oneOUTPUT_LIMIT. No-op:all6default budget-arm attempts failed, off2/2passed. Existing completion checks correctly reject extra/missing unchanged-write proof and incomplete runtime outcomes.

Across retained34IDs this run passed23/34versus26/34in0.17. Declarative benchmark/runtime/grader conditions changed and sampling is stochastic; neither aggregate40/56nor23/34is a controlled cross-version improvement claim. The strongest evidence is the paired within-run modes.

## Vera — precise failure and recovery interaction

All3off runs end JSON_TYPE at root: expectedobject, actualarray, for cases.json. Valid JSON syntax alone is insufficient; the required object wrapper is missing. Each has the same observed sequence: source read succeeds; write hits StaleFileError; a read hits FileNotFoundError; later write/read succeed. Final content remains the wrong root type. Recovered-edit count1clears the stale failure but leaves the missing-file error unresolved. Runtime's explicit unresolved==0guard blocks completion feedback; all3record0feedback despite ample apparent time/steps. This is a joint model/output-contract/recovery-policy problem, not evidence that a larger output budget is needed.

Defaultrepeat1:JSON_PARSE syntax,line1,column3, then empty final response after one feedback round. Exact malformed bytes are not exported; do not infer single quotes/fences. Defaultrepeat2:saved content and readback checks pass, but an earlier write omitted expected_sha256. A later successful write does not auto-clear write schema failures under current conservative policy; runtime remains needs_review. Defaultrepeat3passes after one feedback round and recovered stale edit. Preserve these original failed outcomes; do not regrade by ignoring errors.

Next design candidate: schema-aware JSON proposal/serialization with the existing path/revision/diff approval and strict value checks, plus narrowly proven recovery categories. Never blanket-ignore tool errors or bypass denials. Keep historical failures recorded even if a subsequent supported recovery is verified.

## Orion — blocked before any worker executes

Direct Ada comparison2/2passes,23.874s total,4model requests each. Managed Orion0/2,7.015s total. Each managed attempt:2model requests,2native calls,0dispatches/0verified stages, runtime needs_review. No child ran, so this does not evaluate Ada/Sentinel teamwork or prove orchestration is inherently worse. It exposes a failure before delegation. Provider error codeNONE; no model-output/time budget exhaustion recorded.

The current ZIP drops team.error's detailed rejection type/code and has no manager-tool diagnostic rows. It cannot establish whether the rejected native operation was a bad role/argument, revision mismatch, route or another dispatch guard. Do not guess a specific cause from token counts. Retain private-safe manager tool name, allowed field types, rejection enum and stage in the next export. Reproduce the rejected shape before fixing routing. Consider explicit role enums/application-bound handoff handles rather than requiring a model to copy a64character revision, while retaining the exact stale-file check in application code. Keep the pilot experimental until real dispatch works; direct Ada is the supported comparison winner in these two trials.

## Diagnostic gap found by source inspection

Every trial exports empty target_reads. Runtime computes key=path_key(workspace,path), which uses os.path.normcase, but then compares str(workspace.path(target))==key. On Windows, case/slash normalization makes equivalent paths compare unequal. Read-only synthetic ntpath demonstration confirms normalized-versus-raw mismatch and normalized-versus-normalized equality. This is a concrete emitter defect; fix both sides consistently and add a platform regression in a future code update. Separate TaskEvidence/readback counters still function; empty ordinal arrays do NOT prove that no source/output was read.

End-only observation:Ollama0.40.11, context8192,1loaded model; selected model bytes6194766806andmodel_vram_bytes6194766806(about5.77GiB). This is server-reported selected-model allocation at campaign end, not totalGPUusage, hardware capacity or per-request context proof. No identity/secret/path inference.

## Next-update priorities; not implementation authorization

1. Make rejected manager dispatch observable and reproduce it; simplify role/handoff arguments while preserving application-owned stale checks and permissions.
2. Address Vera's wrong JSON root and precisely scoped error recovery; keep strict grading and original error history.
3. Correct Windows ordinal-path comparison and export tested safe manager/stage reasons; separate actor/stage usage and retained-trace coverage.
4. Begin the next user run with a short targeted Orion/Vera/regression block; retain independent off/default canaries and direct/managed TOTAL-budget comparisons. Preserve benchmark3andversion any semantic/tool/policy change. Keep proposed8Boff adoption scoped to demonstrated roles; test harder cases before broad defaults or a9Bcomparison.

No immediate repeat of this full suite is needed. Existing data is sufficient to design the targeted correction. Do not perform the next app update without a user request. Analysis artifacts: /workspace/artifacts/analysis-4bfd02982444; raw reports: /tmp/aigentics-analysis-4bfd.
