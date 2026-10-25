# README visual assets

The main README uses two original, locally generated SVG graphics, with PNG alternatives for downloads and viewers that do not display SVG. These are documentation assets, not new application dependencies or screenshots of unimplemented features.

| Asset | Purpose | Evidence / provenance |
| --- | --- | --- |
| `assets/midnight-crew-banner.svg` / `.png` | Six-role project identity | Original geometric crown, lens, gear, prism, shield and infinity symbols; role/color direction follows `aigentics/crew.py` and the design record. Not extracted from the user's character artwork. |
| `assets/results-0190.svg` / `.png` | Historical test snapshot | Sanitized aggregate values from [RESULTS_0190_REVIEW.md](../maintenance/RESULTS_0190_REVIEW.md). No raw report, transcript, personal path, credential or model tag is embedded. |
| `screenshots/0160-workbench.png` | Native application layout | Existing synthetic offscreen Qt render documented in [UI_RESEARCH_0160.md](UI_RESEARCH_0160.md). Explicitly labelled as the 0.16 interface milestone in README. |

The result image preserves the distinction between 29 health checks, 24 agent trials and 53 total recorded outcomes. Thinking comparison includes nine matched observations only: Vera 1/3 default versus 3/3 off; Scout 1/2 versus 2/2; Sentinel 1/2 versus 2/2; Unicode 2/2 versus 2/2. Both Sentinel off passes required completion feedback. Two Orion runs delegated to Ada, without a Sentinel child. The four failures and narrow-sample limitations remain visible. The image is not a 0.20 result, a full six-agent team evaluation or a controlled cross-version improvement claim.

Reproduce with a separate Python environment containing Matplotlib:

```bash
MPLCONFIGDIR=/tmp/aigentics-readme-mpl XDG_CACHE_HOME=/tmp/aigentics-readme-cache \
  python docs/design/render_readme_assets.py
```

The renderer reads no user data and calls no model or external image service. Matplotlib is a documentation-generation dependency only and is not added to the desktop package. SVGs contain ordinary vectors and text; no JavaScript, remote font or external resource is used. Rendered PNGs were inspected for text fit, contrast, readable counts and non-black output.
