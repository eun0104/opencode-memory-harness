---
description: Audit and restructure the project's persistent knowledge layer (AGENTS.md, docs/adr, docs/*)
---

Run the `context-curation` skill on this project.

Resolve and read the skill in this order: project-local
`.opencode/skills/context-curation/SKILL.md`, then global
`~/.config/opencode/skills/context-curation/SKILL.md`. If both exist, the project-local copy is the
intentional override. Use scripts, templates, and references only from the copy you loaded, and
follow its Step 0.

Reminders that matter more than the rest:

- Run `scripts/docs_inventory.py` rather than estimating by reading files. Stop if it reports
  `not set up`.
- Step 5 ends with `docs/_tuning-proposal.md` written, every open todo closed, and a **stop**.
  Change nothing else until the user approves item by item.

$ARGUMENTS
