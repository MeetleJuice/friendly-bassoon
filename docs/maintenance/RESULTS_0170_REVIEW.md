# Latest 0.17 result review — sanitized findings

The user uploaded a complete0.17 measurement ZIP and accepted **Orion** as the future coordinator name. Archive CRC, member sizes/SHA256 and the synthetic benchmark digest match. The saved repeated summary was recomputed and matches. Raw exports stay outside Git. The model name is intentionally absent; user explicitly confirmed this is the same8Bmodel as before. The exact tag/quantization are not exported. These are8Bresults, not9Bresults; no fingerprint-based identification is claimed.

## Recorded outcomes

- Health27/27passed; model trials26/34passed,8failed;34m24.344s. All34slots recorded, stop_reason=finished, no skips or interruptions.
-19first-try passes,7feedback-assisted passes;14feedback attempts. Four assisted passes repaired content/final-answer contracts (Sentinel twice, Atlas twice); three repaired operational evidence (Vera once, no-op coordinated twice).
- Generalist George3/3, Scout2/3, Ada3/3, Vera1/3, Sentinel3/3, Atlas3/3. Each role repeated one scenario, so these are not broad reliability certifications. Orion coordinator behavior has not been tested.
-91recorded tool requests,91succeeded,0failed;20actual verified writes,6unchanged writes,6Python static checks. These are recorded execution counters, not proof every session completed or output was correct.
-8failures: Scout1OUTPUT_LIMIT (rejected response4096generated tokens,20398thinking chars,0visible chars/native calls); Vera2(contract/readback); Unicode1exact-byte mismatch; no-op3session deadlines and1provider timeout. Vera first failure remained JSON_PARSE; third repaired JSON but lacked final-output readback. Raw artifacts were not exported, so exact malformed syntax is unknown.
- End-only Ollama observation: server0.40.11, context8192, one loaded model. This does not prove per-turn context, fullGPU placement, totalVRAM or identity of the model.

## Thinking comparison

Four matched pairs: two Unicode and two unchanged-file tasks, same declared/effective budgets and matching advertised controls (defaulttrue, booleanfalse supported). Both modes passed4/4. Requested-off traces contain0exposed thinking chars; defaults42660. Both groups recorded14requests and10native calls. This was not a shortcut that omitted the required tool work.

| Arm | Total seconds (4 trials) | Generated tokens | Feedback repairs |
| --- | ---: | ---: | ---: |
| Model default |300.375|11014|2|
| Thinking off |18.203|437|0|

Observed16.50x duration ratio,93.94%less wall time and96.03%fewer reported generated tokens across these four pairs. Mean Unicode42.672s→4.1485s; no-op107.5155s→4.953s. Important signal, small task coverage, no fixed-seed/hardware isolation/hidden-compute guarantee. Do not apply a universal16x claim to all roles or assign the benefit to9B. User confirms the current8Bproduced these results.

Manifest2=e5efea395071aff13862f9d943e5a9909b1e0a537e0727a2bc51e08bc51a847e. On the30retained IDs this run passed22 versus17in the earlier manifest1 run, descriptively. Prompts/runtime/grader changed; this is not a controlled improvement or permission to regrade earlier results.

## Decisions for planning

Prioritize measured inference profiles and all-role thinking tests. Keep strict bytes/JSON/revision/readback checks; a file can pass content checks while a timed-out run still fails. Improve JSON_PARSE classification/positions without exporting file text, and identify which declared output a read verified using private-safe ordinal roles. Historical George remains generalist; accepted future Orion is a separately versioned coordinator. See UPGRADE_0180_PLAN.md. No application code was changed during this review.
