<!-- memory-harness:start -->
## Memory rules

<!-- L0 budget: 2,000 tokens for this whole file. Adding a line requires removing one. -->

- Plan: `<plan-path>` — owned by the planner. Point to it; never copy it.
- If you cannot recall the current goal, gates, and next action from this conversation (for
  example after compaction), read `docs/handoff/WORKING.md` before any other action.
- Keep WORKING.md current with the `session-checkpoint` skill: after each gate, each decision,
  each failed approach, and before starting the next todo item.
- A todo list holds at most 5 work items followed by one `checkpoint` item.
- Check a gate only with observed evidence: a CHECK you ran, or a concrete EVIDENCE line.
- Before any required stop (waiting for approval, end of session), mark every open todo
  completed or cancelled.
- Start a session with the `session-start` skill; end it with `session-end`.

| Read this | When |
|---|---|
| `docs/decisions.md` | Before proposing an approach that changes a design choice or revisits a rejected alternative |
| `docs/handoff/SESSION-LOG.md` | Search it, never read it whole, when you need what happened in an earlier session |
| skill `context-curation` | About every 5 sessions, when this file exceeds its budget, or when a fact keeps being re-explained |
<!-- memory-harness:end -->
