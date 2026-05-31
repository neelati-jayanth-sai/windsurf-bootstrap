---
description: Refresh this repo's generated Windsurf config (brain, architecture, standards, validate.sh) against the current state of the codebase.
---

<!-- GENERATOR: Save to .windsurf/workflows/sync-windsurf.md. Invoked as /sync-windsurf.
     This persists after the bootstrap folder is deleted. -->

# /sync-windsurf

1. Apply the **windsurf-config-maintenance** skill.
2. Diff the live repo against `.windsurf/BOOTSTRAP_MANIFEST.md`; list what changed
   (layout, dependencies, tooling, commands).
3. Propose updates to the affected rules and `validate.sh`. Show diffs; confirm before
   writing. Respect the char limits.
4. Update `BOOTSTRAP_MANIFEST.md` and tell me to reload Windsurf.

Run this after big dependency bumps, restructures, or when Cascade's project knowledge
feels out of date.
