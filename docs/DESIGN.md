# opencode-memory-harness — Design

Status: draft v3, branch `v3-harness`. This document is the design contract for the rewrite.
It replaces the dependency on the external `session-context-init` and `session-handoff` skills.

## Problem

- One opencode session has a 200k-token window. Auto-compaction fires at about 70% and the
  earliest context (goals, rationale, rejected alternatives) is the part that gets lost.
- oh-my-openagent keeps a todo list running without pausing (a todo-continuation mechanism
  re-prompts the agent while items remain). A long todo list therefore runs inside one session
  until compaction lands in the middle of an item.
- Implementation starts after a discussion with the planning agent. That agent has already
  written the plan file under `.omo/` (or a similar folder), and the first session's window is
  already heavily used when `session-start` runs.
- The previous harness depended on two company-internal skills that are not available here.

## Environment facts (stated by the user)

- AGENTS.md instructions are still followed after compaction.
- Internal LLM (GLM 5.2 based), corporate network, no external dependencies.
- Windows (`C:\projects`); the shell may be PowerShell.

## Principles

1. **AGENTS.md is the anchor.** It is the one layer that survives compaction, so it carries the
   recovery rule: "if you cannot recall the current goal and gates, read WORKING.md first".
2. **Write ahead.** Persist state at event boundaries (gate done, decision made, before a new
   todo item, before a large read). Never wait for "near the limit"; the agent cannot see it
   reliably.
3. **Use the continuation mechanism instead of fighting it.** A checkpoint is a todo item, so
   the mechanism that keeps the agent going also guarantees the checkpoint happens.
4. **Short todo lists.** At most 5 work items, then a checkpoint item. Further items come from
   the plan file after the checkpoint. The tree lives in a file; the session holds a few leaves
   (the unlazy Depth Tree idea).
5. **One fact, one home.** The planner's plan file is the canonical plan. No root `plan.md`
   copy. WORKING.md points to plan items instead of copying them.
6. **Clean stops.** Before any required stop (approval boundary, end of session), mark every open
   todo completed or cancelled so the continuation mechanism does not push past the stop.
7. **Evidence gates (unlazy).** A gate is checked only with a runnable `CHECK:` whose result was
   observed, or an `EVIDENCE:` line with a concrete value, output, or path. Never "pending".
8. **Small skills.** Each session skill body stays under about 1,500 estimated tokens, because
   the skill is loaded into the same window it is trying to protect.
9. **Portable tooling.** Python standard library only. Skill instructions do not rely on `grep`,
   `sed`, or other POSIX-only commands.

## Skills

| Skill | When | Does |
|---|---|---|
| `session-start` | First session after planning; every later session start; after compaction | First run: capture planning rationale, create WORKING.md and the AGENTS.md anchor, then recommend a fresh session. Later: read WORKING.md, then only what it points to |
| `session-checkpoint` | During a session, at event boundaries and as todo items | Rewrite WORKING.md: goal, gates with evidence, next action, decisions, do-not-repeat, in flight |
| `session-end` | End of session | Close WORKING.md for the next session, append SESSION-LOG.md with tags, offer a Git checkpoint |
| `context-curation` | About every 5 sessions | Existing skill, slimmed: promote recurring facts to L2, audit budgets and reachability |

The old pre-init curation pass is removed from the first session. The first session is already
heavy after planning; a full curation run there would push it into compaction. `session-start`
does the minimum instead, and curation runs later when there is session evidence.

## Files

| File | Layer | Owner | Notes |
|---|---|---|---|
| `AGENTS.md` | L0 | session-start (creates), curation (tunes) | Anchor rules + routing. 2,000-token cap |
| `.omo/` plan file | L1 | planner | Canonical plan. Path recorded in AGENTS.md; pointed to, never copied |
| `.omo/` notepads (if present) | L3 source | oh-my-openagent executor | Per-plan learnings / decisions / issues. Harness does not duplicate them |
| `docs/handoff/WORKING.md` | L1 | session-checkpoint, session-end | Live state. Replaces the old HANDOFF.md: one file, always current |
| `docs/handoff/SESSION-LOG.md` | L3 | session-end | Append-only, tagged, searched not read |
| `docs/decisions.md`, `docs/rules/`, `docs/domain/`, `docs/reference/` | L2 | context-curation | Facts that outlive one plan, promoted from notepads and the session log |

HANDOFF.md is merged into WORKING.md. If WORKING.md is kept current during the session, a
separate end-of-session snapshot would state the same facts twice.

### Division of labour with oh-my-openagent

oh-my-openagent already keeps per-plan notepads. The harness does not write a parallel
decisions or gotchas file during execution; that would state the same fact in two places.

- **Notepads** hold what the executor learns inside one plan (raw material).
- **WORKING.md** holds the state needed to resume after compaction: current leaf, gates with
  evidence, next action, in-flight files. The notepads do not carry gate evidence or the exact
  next action.
- **L2 docs** hold facts that must outlive the plan. context-curation harvests the notepads and
  the session log, and promotes what passes the promotion test. A finished plan's notepads are
  otherwise easy to lose track of.

Plan lookup: the path is known exactly once, when the plan has just been written and is still
in context. session-start records it as one line in AGENTS.md, which survives compaction, so
every later session and every recovery reads it from there. The harness never hard-codes the
`.omo/` layout.

- New or switched plan: update that one AGENTS.md line right after planning, while the path is
  still in context.
- Path not in context (e.g. session-start runs in a fresh session): list the `.md` files under
  `.omo/` and ask the user which one is the plan. Do not guess.
- Whether `.omo/` is git-ignored and whether notepads exist are checked on the spot
  (`git check-ignore`, a directory listing), not assumed.

## First session after planning

The window is already heavy and the planning rationale exists only in the conversation. Order
the writes by loss risk:

1. Take the plan path from context (the plan was just written). Do not re-read the plan.
2. Write the planning rationale (chosen approach, rejected alternatives and why) that is not
   already in the plan file. The plan usually records *what*, not *why*. Destination: the
   plan's notepad `decisions.md` if one exists at this point, otherwise `docs/decisions.md`.
3. Write WORKING.md with the first leaf goal and its gates, pointing to the plan item.
4. Write the minimal AGENTS.md with the anchor rules and the plan path.
5. Close all open todos and recommend starting implementation in a fresh session.

## Open questions

- Names of the continuation and compaction hooks in the internal oh-my-openagent build, and
  where the 70% threshold is configured. Not blocking; the design does not depend on them.
- Whether the executing agent ticks checkboxes in the plan file. Observable in use; if it does,
  WORKING.md can rely on the plan for progress and keep only the current leaf.
