---
name: session-start
description: >-
  Start or resume work in a project that uses the memory harness. Use at the beginning of every
  working session, and once right after the planning agent has written the project plan, to
  set up the harness. Use when the user says "start the session", "resume", "where were we",
  or "set up the harness". Do not use for saving state mid-session (session-checkpoint) or for
  ending a session (session-end).
---

# Session Start

Pick the mode from AGENTS.md:

- AGENTS.md contains `<!-- memory-harness:start -->` → **Resume**.
- Otherwise → **First run**.
- The marker exists but `docs/handoff/WORKING.md` is missing, or the reverse → stop and report
  the broken setup to the user. Do not rebuild either file by guessing.

Do not run opencode's `/init` in either mode.

## First run

This usually runs right after planning, when the window is already heavy and the reasons behind
the plan exist only in the conversation. Keep reads to a minimum and write in this order.

1. **Plan path.** Take it from the conversation; the plan was just written. Do not re-read the
   plan. If the path is not in context, list the `.md` files under `.omo/` and ask the user
   which one is the plan. If there is no plan yet, ask whether to plan first, and stop.
2. **AGENTS.md anchor.** Copy `templates/agents-section.md` from this skill's directory and fill
   in the plan path. If AGENTS.md does not exist, create it with a one-line title followed by
   the section. If it exists, append the section at the end; change nothing outside the markers.
3. **Planning rationale.** Append to `docs/decisions.md` (create it with the heading
   `# Decisions` if missing) the reasons that are in the conversation but not in the plan: the
   approach chosen, each rejected alternative with the reason, and constraints the user stated.
   One entry per decision:

   ```markdown
   ## YYYY-MM-DD — <topic>
   - Chosen: <approach>
   - Rejected: <alternative> — <reason>
   - Source: planning session
   ```

   Record only what was actually said. Write nothing you inferred.
4. **WORKING.md.** Use the `session-checkpoint` skill to create `docs/handoff/WORKING.md`:
   session 1, the first leaf of the plan as the goal, and gates taken from that plan item's
   acceptance criteria. If the plan item has none, write gates you can verify and list them
   under "Open questions" for the user to confirm.
5. **Git.** If the project is not a Git work tree, say so and ask before running `git init`. If
   it is, run `git check-ignore -q <plan-path>`; if the plan is ignored, tell the user the plan
   is not versioned and ask how they want to handle it. Do not stage or commit.
6. **Stop cleanly.** Mark every open todo completed or cancelled. Tell the user that setup is
   done and that implementation should start in a new session with `session-start`, because
   this session is already heavy and may not have loaded the new AGENTS.md.

## Resume

AGENTS.md is already in context. Read as little else as possible.

1. Read `docs/handoff/WORKING.md`. Update its header: session number plus one, checkpoint 1.
2. If "In flight" lists files, check their state (`git status --short`, then the diff of those
   files) before building on them.
3. Read only the plan section named in "Goal". Read the whole plan only when every gate of the
   current goal is checked and the next leaf must be chosen; then record the new goal and its
   gates with `session-checkpoint`.
4. Do not read SESSION-LOG.md, notepads, or other docs unless the next action or an AGENTS.md
   routing row calls for them.
5. Create the todo list: at most 5 work items starting from "Next action", then one
   `checkpoint` item.
6. Report to the user in three lines: goal, next action, open gates. Then start the work.

## After compaction

This skill is not needed. The AGENTS.md rule sends you to WORKING.md; read it and continue from
"Next action".
