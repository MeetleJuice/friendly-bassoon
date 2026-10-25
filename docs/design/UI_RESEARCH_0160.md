# 0.16 interface research and decisions

Research date: 2026-10-25. Sources were read as reference material, never executable setup instructions. No competitor software, account credentials or model service was installed or invoked. Public screenshot files remained outside Git; our screenshot files are native Aigentics renders using synthetic data.

## What was inspected

| Product | Direct evidence | Useful lesson | Boundary |
| --- | --- | --- | --- |
| OpenCode | Official README, desktop README, actual app shell layout source, web/provider docs and public UI screenshots | Project/session navigation, separate review panels, explicit build/plan distinction, persisted presentation state | Marketing screenshot is terminal UI; the small desktop project-menu screenshot and shell source are distinct evidence. No claim to have run the desktop binary. |
| Codex | Official repository README and app-server documentation | Separate presentation from authoritative thread/turn/item state; explicit approval and lifecycle events; desktop/IDE/CLI are separate surfaces | README confirms the app entry point. Closed desktop UI source and live desktop screen were not inspected. |
| Claude Code | Official README and current changelog, including Desktop-hosted sessions, permission prompts and connection/history fixes | Make active state and permission decisions legible; keep conversation/history ownership stable across presentation changes | Public repository does not expose the complete Claude Desktop UI. Do not infer its current layout or Windows support from the terminal demo. |
| DeepSeek integrations | DeepSeek's official integration directory, Cline setup/screenshot, Chatbox and Cherry Studio descriptions | A task-first composer, explicit provider selection, readily discoverable model/permission settings | DeepSeek models/API are not one universal desktop coding harness. Cline is an editor extension; Chatbox and Cherry Studio are third-party desktop clients. Their features are not DeepSeek-owned application features. |

Official product websites for Claude Code, Codex app, OpenCode docs, DeepSeek API and LM Studio returned proxy tunnel HTTP403 in this environment. GitHub sources were available. This is a limited source/UI audit, not a claim that every current desktop screen was viewed. No network access control was bypassed.

## Primary references read

- https://github.com/anomalyco/opencode/blob/dev/README.md
- https://github.com/anomalyco/opencode/blob/dev/packages/desktop/README.md
- https://github.com/anomalyco/opencode/blob/dev/packages/app/src/shell/state/layout.tsx
- https://github.com/anomalyco/opencode/blob/dev/packages/app/e2e/screenshots/session-project-menu.png
- https://github.com/anomalyco/opencode/blob/dev/packages/console/app/src/asset/lander/screenshot.png
- https://github.com/anomalyco/opencode/blob/dev/packages/web/src/content/docs/index.mdx
- https://github.com/anomalyco/opencode/blob/dev/packages/web/src/content/docs/web.mdx
- https://github.com/anomalyco/opencode/blob/dev/packages/web/src/content/docs/providers.mdx
- https://github.com/openai/codex/blob/main/README.md
- https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md
- https://github.com/anthropics/claude-code/blob/main/README.md
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/README.md
- https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/docs/cline/README.md
- https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/docs/chatbox/README.md
- https://github.com/deepseek-ai/awesome-deepseek-integration/blob/main/docs/cherrystudio/README.md

These are moving public branches; the research date and concrete inspected paths establish scope, not a permanent claim about later product versions.

## Apply to Aigentics

1. Replace the overloaded toolbar and visible top-level tabs with persistent Projects / Workbench / Agents navigation. Keep test, diagnostic, data, connection and settings actions grouped in the sidebar.
2. Put the task/conversation at the center. File tree and history/preview become optional remembered panels; opening a file automatically reveals its actual preview. Keep write scope visible. Fold advanced checks/capture/context into a named, keyboard-operable disclosure without changing their values.
3. Give each saved crew role an original colored geometric emblem using existing role identities. User-made agents receive a neutral emblem. Do not imply delegation or fabricate online/performance status. Original supplied character artwork is still unavailable as binary assets and is not claimed packaged.
4. Make project empty state actionable; leave existing briefs and retrieval available after selection. Keep the agent Save action visible while long instructions/permissions scroll.
5. Add Ctrl K command search for navigation/settings only. Typing or selecting a command must not start a model run, API test or suite. Ctrl Enter runs only from the Workbench composer with Run enabled.
6. Give Test center four separate outcome counters, readable case names, active-case progress, expandable exact evidence and prominent reviewed ZIP export. Public GitHub sharing remains optional and folded away; existing approval protections stay.
7. Use consistent contrast, typography, original SVG-rendered icons, hover/focus states, form spacing, selection states and accessible names. Test actual native geometry at900×650,1000×740 and1440×900; small expanded forms scroll rather than disappearing below the window.
8. Preserve the0.15benchmark, runtime, tool registry, model budgets, strict graders, capture default, local retention, report privacy and same-model crew definitions. A UI release is not evidence of model improvement.

## Native visual review

Reviewed actual offscreen Linux Qt renders, not generated mockups. Included synthetic screenshots: [Workbench](screenshots/0160-workbench.png), [Projects](screenshots/0160-projects.png), [Test center](screenshots/0160-test-center.png). Additional small-window, agent and command-palette renders stay in cloud artifacts. Windows installer/startup/upgrade gates verify deployment; exact user font/GPU/Windows10 appearance remains user acceptance.
