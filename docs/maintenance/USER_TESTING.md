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
