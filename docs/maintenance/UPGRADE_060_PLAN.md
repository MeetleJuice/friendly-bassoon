# 0.6 update: evidence from working agents

Approved scope: implement and publish a tested update. Issues #5–#8 show Qwen2.5-Coder14b returns text requests on every tested route, while the user's Qwen3:8b session performs native approved writes. Seventeen offline checks and five catalog connections pass. A saved file is not a launched/tested game. Original user logs/paths/code stay out of Git.

Deliver:
- Explain diagnostic outcomes in plain language, distinguish app checks/model checks, show progress and actionable next steps.
- Automatically compile-check Python writes without executing/importing code; flag obvious literal unpacking mistakes like the observed dimensions assignment. Offer an explicit selected-project-file check without a model request.
- Keep hashes and approval checks, but allow a run-scoped `last_read` revision reference so models need not transcribe hashes. Revalidate before/after approval. Classify recovered edit failures separately from unresolved errors.
- Supply agent identity and explicit read-only planning mode; never execute model prose.
- Save bounded structured validation/recovery/assessment evidence and allow preview-approved sharing of an individual run without copying transcripts.
- Add synthetic regressions and packaged checks, preserve existing data/settings/agents, verify the actual 0.5 installer upgrade and publish a fresh immutable release.

Not claimed: universal Ollama repair, automatic gameplay verification, cloud model certification, arbitrary background execution, embeddings, or a new OS sandbox. Syntax/static checks cannot prove dependencies, graphics/audio or game behavior. No extra cloud requests or automatic uploads.
