---
name: session-end
description: >-
  Close a working session in a project that uses the memory harness: make WORKING.md ready for
  the next session, append a tagged entry to the session log, suggest curation when due, and
  offer a Git checkpoint. Use when the user says "wrap up", "end the session", "handoff", or
  "let's stop here". Do not use for mid-session saves; that is session-checkpoint.
---

# Session End

The next session starts from WORKING.md alone. Everything it needs must be there or one pointer
away, and nothing stale may remain in it.

## 1. Final checkpoint

Use `session-checkpoint` to bring WORKING.md fully up to date. Then check two sections harder
than usual, because the next reader has none of this conversation:

- **Next action**: specific enough to start cold. "Continue the fitting" fails; "Run
  `fit_mobility.py` on `data/run07.csv` with the T-dependent model and compare to G2" passes.
- **In flight**: every edited file that is not yet verified. Check `git status --short` rather
  than recalling from memory.

## 2. Append the session log

Append one entry to the end of `docs/handoff/SESSION-LOG.md` (create the file with the heading
`# Session Log` if missing). If a `## Session NNN — in progress` heading from a checkpoint
overflow exists, change that heading to the final form below and add the rest under it.

```markdown
## Session NNN — YYYY-MM-DD

### Did
- <what changed, briefly; name files>

### Gates closed
- G1 <criterion> — <evidence, one line>

### Learned
- [decision] <chose X over Y because Z>
- [gotcha] <tool, data, or external system behaved unexpectedly>
- [candidate] <fact that may deserve a permanent home>
```

Keep the `## Session NNN` heading exactly in this form; curation finds sessions by it. Tag every
learned line; untagged lines are invisible to the next harvest. Write `none` under an empty
heading. Never edit earlier entries.

## 3. Close WORKING.md

Rewrite WORKING.md for the next session:

- Remove "Decisions this session" lines; they are now in the log. Write `none`.
- Keep "Do not repeat" lines that still apply to the current goal. Remove lines about a goal
  that is finished.
- If every gate of the goal is checked, leave the goal as is and set Next action to "Choose the
  next leaf from the plan". The next session-start will do that with the plan in front of it.
- Set the header to `Closed: YYYY-MM-DD HH:MM · Session NNN`.

Do not edit the plan file. The planner owns it.

## 4. Curation check

Read `docs/handoff/.curation-state.json` if it exists. Suggest running `context-curation` when
any of these hold; suggest, do not run it:

- 5 or more sessions since `last_tuned_session`, or no state file after 5 sessions
- AGENTS.md is longer than its 2,000-token budget
- 3 or more `[candidate]` or `[gotcha]` lines since the last tuning
- The user had to re-explain something the agent should have known

## 5. Git checkpoint

Offer a checkpoint; never make one without approval.

1. Run `git rev-parse --show-toplevel`. If it fails, say the project is not under Git and ask
   whether to run `git init`. Declining does not block the handoff.
2. Run `git status --short` and `git diff --cached --name-only`. If nothing changed, say so.
3. Show the changed paths and propose a commit: the exact literal paths and a one-line
   message. Show already-staged paths separately and do not include them silently.
4. Only after the user approves the paths and the message, run `git add -- <path>...` and
   `git commit -m "<message>"`. Never use `git add -A`, `git add .`, or wildcards.
5. Never push, switch or create branches, stash, reset, rebase, or amend here.

If the user declines, list the uncommitted paths in WORKING.md "In flight".

## 6. Stop cleanly

Mark every open todo completed or cancelled. Report in three lines: what was done, the next
action, and whether a checkpoint commit was made.
