---
description: Undo a windsurf-bootstrap run by removing the generated .windsurf configuration listed in BOOTSTRAP_MANIFEST.md. Run before deleting the bootstrap folder if you want to revert.
---

# /teardown-windsurf

Use this only to **revert** a bootstrap run. (If you're happy with the config, you don't
need this — just delete the `windsurf-bootstrap/` folder; the generated config stays.)

1. Read `<repo-root>/.windsurf/BOOTSTRAP_MANIFEST.md` and list every file it records as
   created (skip ones marked *updated*/*merged* — those existed before; for those, offer
   to restore from git instead of deleting).
2. Show me the full list and ask for explicit confirmation.
3. On confirmation, delete the created files (rules, skills, workflows, `validate.sh`,
   and the bootstrap-added `hooks.json` entry — remove only the entry, not a pre-existing
   file).
4. Remove now-empty `.windsurf/` subdirectories.
5. Report what was removed and remind me to reload Windsurf.

Never delete files not attributable to this bootstrap run.
