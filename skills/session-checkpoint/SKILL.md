---
name: session-checkpoint
description: >-
  Save the live session state to docs/handoff/WORKING.md so it survives context compaction.
  Use at every event boundary during work: after a gate passes or fails, after a decision
  between alternatives, before starting the next todo item, before reading a large file or
  running a long command, and whenever a todo item named "checkpoint" comes up. Also use when
  the user says "checkpoint" or "save state". Do not use for end-of-session wrap-up; that is
  session-end.
---

# Session Checkpoint

Compaction can happen at any moment, and whatever is only in the conversation may be lost.
WORKING.md is the copy that survives. A checkpoint costs a small write; a missed one costs the
reasoning since the last one.

## When

Write a checkpoint at each of these moments. Do not wait until the context feels full; you
cannot see that reliably.

- A gate passed, failed, or was abandoned
- A decision was made between alternatives
- An approach failed (add it to "Do not repeat")
- Before starting the next todo item
- Before reading a large file or running a long command
- A todo item named "checkpoint" is next

## Todo list rule

When you create or extend a todo list, put at most 5 work items in it, followed by one item
named `checkpoint`. After the checkpoint, take the next items from the plan file. This keeps
the list short and makes the checkpoint happen even when work continues automatically.

## How

1. If `docs/handoff/WORKING.md` does not exist, create it from `templates/WORKING.md` in this
   skill's directory.
2. Rewrite the whole file. Do not append. Update the header line: date and time, session
   number, and checkpoint number plus one.
3. Fill every section. Write `none` for an empty one; an omitted section looks forgotten.
4. **Goal**: the current plan leaf and a pointer to its plan item. Do not copy plan text.
5. **Gates**: one line per acceptance criterion.
   - Check a gate `[x]` only with evidence observed in this session: a `CHECK:` command you
     ran whose output matched `EXPECT:`, or an `EVIDENCE:` line with a concrete value, output
     excerpt, or file path.
   - Never write "pending", "should work", or "looks fine" as evidence.
   - To drop a gate, replace it with `ABANDONED: <reason>`. Do not delete it silently.
6. **Next action**: the exact next step, specific enough to start without re-reading anything.
7. **Decisions this session**: tag each line `[decision]`. Include the rejected alternative and
   the reason.
8. **Do not repeat**: failed approaches with the reason, so they are not proposed again.
9. **In flight**: files edited but not yet verified.

## Size

Keep WORKING.md under about 1,200 tokens. If it grows past that, move the oldest
"Decisions this session" lines to the end of `docs/handoff/SESSION-LOG.md` under a heading
`## Session NNN — in progress`, keeping their tags. Keep the other sections in WORKING.md.

## Do not

- Summarize the conversation. Record state, not narrative.
- Copy content from the plan or other docs. Point to it.
- Check a gate without evidence.
- Stop the work for a checkpoint. Write it and continue with the next action.
