## 0.11 acceptance

Update/install/restart and let suite4 run once with the remembered local Ollama agent in Balanced mode. It now has18live cases plus23offline checks; no actual API list/key checks occur in this suite. The standalone Test APIs button remains. New ordered native cases include empty/Unicode/multiline/nested outputs, two files, two-input transformation, unchanged writes and a deliberately stale hash followed by verified recovery. The expected stale rejection/denied approval is a successful safety exercise, not a reason to retry until green. Inference can take up to45minutes at configured bounds; Cancel keeps partial evidence.

Review both exact previews, approve opening both drafts, click Create on each GitHub page, and provide issue URLs. Compact case rows have a legend; full traces stay local. Compare only matching suite/mode/agent settings. No generation used by separate manual model-list metadata checks, but those have been removed from automatic testing to reduce noise.

For task plans, try two small steps editing the same disposable file. Run → inspect → verify first checkpoint, then run → inspect → verify second. Earlier hashes remain historical; later accepted revisions become effective. Refresh/reconcile a linked finished run to inspect it after interruption; failed/interrupted work cannot be checkpointed as success. Inspect files/effects before reset. No automatic Ralph restart or tool replay.

## 0.10 acceptance

Update/install/restart and let suite3 run in Balanced mode with your remembered local agent. It can take longer (up to30minutes at the allowed bounds); Cancel preserves partial evidence. Review/submit both GitHub drafts and provide links. If a controlled comparison is useful, select Legacy explicitly for one separate run; never rerun silently to get a pass.

For Task plan: open a disposable project → Workbench → Task plan → Add step (task/acceptance criteria and relative expected files). Select Run step. Inspect the actual diff and results. Reopen Task plan → Verify checkpoint only when you accept the actual result. A later step requires prior accepted file revisions still matching. Changed files, uncertain attempts and missing history require inspection/reset, not blind continuation. Plans are local metadata, not automatic code commits or an autonomous Ralph loop.

## 0.9 acceptance

Click Update from0.8 and install/restart. The queued suite2 uses your remembered local agent. Simple cases advertise just their required tool; file-write cases additionally expose read_file. Edit/Python output caps are2048; simple cases1024. No commands/cloud fallback/replay. A new suite identity prevents misleading comparisons with suite1. When finished, inspect both exact previews, approve opening the two drafts, click Create on both GitHub pages and provide both URLs. Report typed tool errors and provider limits as useful data, not reasons to rerun until green.

## 0.8 guided acceptance

After first updating from0.7, click **Test suite**, choose your working local Ollama agent, and click **Go**. The screen lists all ten tests. Go authorizes the listed temporary output edits; denial test rejects its edit automatically. No project files/commands/cloud models are used. Allow roughly ten minutes; Cancel keeps partial data. Disabled tools show skipped. The completion sound means review is ready, not that every case passed.

Review both exact public previews at the bottom. Check the shared approval box and click **Open both approved GitHub drafts**. In your browser, click **Create** on each page, then send both issue links here. Browser drafts are not submissions. You do not need a token. Local detailed metadata remains under existing retention settings; model names remain excluded publicly. A failed test is useful data—do not rerun repeatedly just to get a green result.

Future Update clicks download/verify, ask to install, then run this workflow once after the target version restarts. Existing0.7 lacks this queue, hence the first manual Test suite click.

# One useful 0.7 acceptance test

1. Update to 0.7.0 and restart. Keep your saved Qwen3:8b or Qwen3.5:9b agent; no new download is needed.
2. In Workbench, open a disposable project and choose Build/edit. Leave **New task · fresh context** selected.
3. Enter: “Create upgrade_check.py containing a square(number) function that returns number * number. Use real Python line breaks. Request approval, then read it back. Do not run commands.”
4. Confirm **Expected output files** shows upgrade_check.py. This visible field limits file-tool writes; change/clear it deliberately for other tasks. Keep **Read back output files** checked. Optionally check Require real tools or choose specific Required tools.
5. Run once. Approve only the intended diff. The app should create the named file, pass its static check and verify the post-write read-back. A different write target is blocked. Identical writes are skipped and do not satisfy a required actual write.
6. If the model gives no final answer, inspect the application's preserved evidence summary. Do not repeat the whole task blindly; successful writes are already present.
7. Inspect the real file and requested behavior. Choose Goal met or Needs work, then Share run report; inspect/approve the preview and finish Create on GitHub. Send the posted issue link plus one sentence describing expected/actual behavior. Public reports omit filenames/tasks/notes.

For a read-only audit, leave output files empty and use Require real tools/Required tools. Plan mode blocks writes/commands. Continue conversation and Resume explicitly supply historical conversation text; writing “new execution” in a prompt does not change that setting.

Diagnose runs 21 built-in checks in disposable folders, plus optional update/local model checks. Test APIs remains generation-free metadata only. Cloud generation remains explicit; no hidden retries, model switching, automatic uploads or OS command sandbox were added. Syntax/static checking does not launch or certify the program. Keys stay on your computer.
