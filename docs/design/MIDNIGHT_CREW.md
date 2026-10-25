# Midnight Crew visual direction

The user supplied a six-column character-sheet image in chat on October 24, 2026, titled **AIGENTICS — THE MIDNIGHT CREW**, with the caption “Six agents. One higher intelligence.” It is the requested future visual direction, rather than a claim that autonomous collaboration is implemented.

## Reference and asset status

The original image is visible in the conversation but was not exposed as a downloadable file ID or local image file in this execution workspace. Searches of the accessible attachments, shared files, and library files found no original. **No raster copy of the user's artwork is committed.** This document faithfully records the design reference so the direction survives a fresh development context. A future attachment with a downloadable file reference can be saved unchanged to `docs/design/midnight-crew-reference.png` with its actual format and provenance. Do not substitute a generated approximation and call it the original.

Art production is deferred in favor of functional agents and evaluations. The role-color and emblem metadata in `aigentics/crew.py` are implementation identifiers and approximate design tokens, not colors sampled from the source image.

## Character direction

| Agent | Role | Character and emblem | Color direction |
| --- | --- | --- | --- |
| George | Generalist | Crown-wearing dark familiar with glowing blue eyes, staff/orb, and compass-star emblem. | Midnight blue, electric blue, pale blue. |
| Scout | Investigator | Large-eared fox-like familiar with goggles, scarf, and magnifying glass; magnifying-glass emblem with leaves. | Teal and turquoise. |
| Ada | Builder | Horned mechanical familiar with bronze goggles, gears, and workshop props; gear-star emblem. | Bronze, amber, warm gold. |
| Vera | Test engineer | Purple crystal familiar with spectacles, floating shards, and an open book; faceted crystal-diamond emblem. | Lilac, violet, pale lavender. |
| Sentinel | Reviewer | Armored horned familiar with red eyes, shield, and a defensive stance; shield-star emblem. | Crimson and dark red. |
| Atlas | Continuity | Hooded scholarly familiar with orbiting documents, celestial motifs, and a glowing book; infinity-orbit emblem. | Indigo, violet, cool white. |

The reference uses individual portrait cards, large agent names, role labels, short role verbs, quotations, emblem studies, expression/pose variations, and color swatches on a dark celestial background.

## Future UI application

- Keep each agent's name and role readable alongside its color and symbol. Color alone must never convey status or permissions.
- Add portraits and small emblems once appropriately sized assets are available; preserve clear keyboard focus, contrast, and tooltips.
- Distinguish agent identity from execution state. Success, failure, stopped, waiting for approval, and not yet tested need separate labels.
- Show model, instruction version, permissions, and tested capabilities in a compact details panel. Artwork must not imply greater capability than evaluation evidence establishes.
- Keep expressions and animations decorative. Reduced-motion settings and clear textual progress should remain possible.
- George does not gain delegation powers from his crown or coordinator motif. Specialists remain individually selected until separately implemented orchestration passes its own evaluations.

## Functional source of truth

`aigentics/crew.py` defines the versioned roster and coarse visual metadata. Each saved agent is editable. Re-running roster setup adds missing definitions without replacing personal settings. Controlled evaluations use fresh baseline definitions with the selected model rather than mutating saved user agents.


## Expanded reference set — October24,2026

The user supplied seven additional inline images: six individual character portraits and a six-column emblem sheet. George occupies a blue celestial observatory with crown and galaxy orb; Scout investigates in a teal library with magnifier and goggles; Ada builds in an amber mechanical workshop with articulated tools; Vera floats among violet crystals with spectacles and a book; Sentinel carries a crimson shield in an armored hall; Atlas appears as an indigo owl scholar with orbiting pages and books. The emblem sheet names Nexus Crown, All-Seeing Lens, Forge Spark, Truth Prism, Crimson Aegis, and Eternal Archive. It includes large emblems, primary square icons, simplified variants, monochrome outlines and small UI icon studies. Names, readable role labels and text status must accompany color. Portraits should support a future roster gallery, not obscure task evidence or imply implemented orchestration.

These images are visible in chat but no downloadable file IDs or local binaries were exposed. The exact seven originals are therefore **not archived**. Save original file attachments unchanged under docs/design/reference/ when available; do not generate replicas and describe them as originals. Functional completion/verification work proceeds independently.


## 0.16 native identity

Original lightweight geometric emblems now render in the saved agent library and navigation, using existing crew role colors. They are independent native symbols, not extracted character artwork or a claim that the user's original image binaries were archived. See UI_RESEARCH_0160.md and its actual synthetic Aigentics screenshots. No third-party logos/screenshots are packaged.
