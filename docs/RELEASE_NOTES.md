# 0.14.1 — preserve long campaign reports

- Fixes “Diagnostic report exceeds the storage limit” for long66attempt campaigns using compact lossless JSON and a separate bounded1MBcampaign allowance. Other reports retain250KBcaps; global retention limits remain.
- Preserves all recorded trace/correctness evidence rather than dropping older results.
- After updating, automatically continues a matching interrupted campaign. Previously committed attempts remain; an unknown in-flight attempt is marked interrupted and never silently replayed.
- No changes to campaign cases, model budgets, agent permissions or public sharing approval. Existing0.14campaign scope remains compatible.

Windows install/upgrade from0.14/data-preservation/silent-restart and public updater verification gate delivery. The last unsaved attempt from a failed process cannot be reconstructed.
