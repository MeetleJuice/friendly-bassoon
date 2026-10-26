# README visual assets

The main README uses original, locally generated SVG graphics, with PNG alternatives for downloads and viewers that do not display SVG. These are documentation assets, not new application dependencies or screenshots of unimplemented features.

| Asset | Purpose | Evidence / provenance |
| --- | --- | --- |
| `assets/midnight-crew-banner.svg` / `.png` | Six-role project identity | Original geometric crown, lens, gear, prism, shield and infinity symbols; role/color direction follows `aigentics/crew.py` and the design record. Not extracted from the user's character artwork. |
| `assets/results-0190.svg` / `.png` | Historical test snapshot | Sanitized aggregate values from [RESULTS_0190_REVIEW.md](../maintenance/RESULTS_0190_REVIEW.md). No raw report, transcript, personal path, credential or model tag is embedded. |
| `assets/report-profiling-0200.svg` / `.png` | Developer report-processing profile | Single local before/after cProfile observations of the same synthetic 64-case campaign, recorded in the [0.20 plan](../maintenance/UPGRADE_0200_PLAN.md) and [engineering log](../ENGINEERING_LOG.md). Distinct from the 0.19 live-model graph. |
| `screenshots/0160-workbench.png` | Native application layout | Existing synthetic offscreen Qt render documented in [UI_RESEARCH_0160.md](UI_RESEARCH_0160.md). Explicitly labelled as the 0.16 interface milestone in README. |

The result image preserves the distinction between 29 health checks, 24 agent trials and 53 total recorded outcomes. Thinking comparison includes nine matched observations only: Vera 1/3 default versus 3/3 off; Scout 1/2 versus 2/2; Sentinel 1/2 versus 2/2; Unicode 2/2 versus 2/2. Both Sentinel off passes required completion feedback. Two Orion runs delegated to Ada, without a Sentinel child. The four failures and narrow-sample limitations remain visible. The image is not a 0.20 result, a full six-agent team evaluation or a controlled cross-version improvement claim.

The developer profile graph shows redactor call count 385,502 → 58,255 and profiled test wall time 16.14 → 13.49 seconds. Report-save cumulative time is separately labelled 8.632 → 5.234 seconds; cumulative function time is not interchangeable with whole-test wall time. All 177 diagnostic snapshots were retained. These are single observations under profiling, not a statistically controlled benchmark or evidence of model/user-Windows speed improvement. The bounded memo reuses repeated redactions within one scrub traversal; original redaction rules and production SQLite durability are unchanged. Nothing in the graph claims a published installer.

Reproduce with a separate Python environment containing Matplotlib:

```bash
MPLCONFIGDIR=/tmp/aigentics-readme-mpl XDG_CACHE_HOME=/tmp/aigentics-readme-cache \
  python docs/design/render_readme_assets.py
```

The renderer reads no user data and calls no model or external image service. Matplotlib is a documentation-generation dependency only and is not added to the desktop package. SVGs contain ordinary vectors and text; no JavaScript, remote font or external resource is used. Rendered PNGs were inspected for text fit, contrast, readable counts and non-black output.
