# 0.14.1 — preserve long campaign reports

- Fixes “Diagnostic report exceeds the storage limit” for long66attempt campaigns using compact lossless JSON and a separate bounded1MBcampaign allowance. Other reports retain250KBcaps; global retention limits remain.
- Preserves all recorded trace/correctness evidence rather than dropping older results.
- After updating, automatically continues a matching interrupted campaign. Previously committed attempts remain; an unknown in-flight attempt is marked interrupted and never silently replayed.
- Adds Review / save diagnostic ZIP in Campaign and Diagnose. Partial results can be reviewed and saved without completing tests or approving GitHub sharing. Drag the saved ZIP into support chat; nothing uploads automatically. Static filenames, hashes and bounded sanitized numeric traces retain useful evidence without private content.
- No changes to campaign cases, model budgets, agent permissions or public sharing approval. Existing0.14campaign scope remains compatible.

Windows install/upgrade from0.14/data-preservation/silent-restart and public updater verification gate delivery. The last unsaved attempt from a failed process cannot be reconstructed.
