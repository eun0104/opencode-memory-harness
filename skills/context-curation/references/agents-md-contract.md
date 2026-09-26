# AGENTS.md Contract

Read before editing AGENTS.md.

AGENTS.md is not documentation. It is a **routing table with a few rules attached**, and in this
harness it is also the one layer that survives compaction. Every line competes for the same
fixed budget on every session and after every recovery.

## Structure

```markdown
# <Project> — Agent Instructions

## Invariants                     <- at most about 7 one-line rules, verbatim
## Project shape                  <- at most 10 lines, only if navigation is non-obvious

<!-- memory-harness:start -->
## Memory rules                   <- written by session-start from its template
- Plan: `<plan path>`
- ...recovery, gate, checkpoint, todo, Git, and stop rules...

| Read this | When |           <- the routing table
<!-- memory-harness:end -->
```

## Who edits what

| Part | Curation may |
|---|---|
| Memory rules inside the markers | Not change them. They come from the `session-start` template; propose improvements in section G |
| `- Plan:` line | Update only when the user confirms the plan moved |
| Routing table inside the markers | Add, reword, reorder, or remove rows |
| Invariants and project shape outside the markers | Add, reword, or remove after approval |

Never remove the markers. The inventory and `session-start` find the section by them.

## Allowed

- Routing rows with trigger conditions
- Invariants, one line each, each pointing to its rules file
- A short project-shape sketch when navigation is genuinely non-obvious

## Not allowed

- Rationale or history → an ADR
- Architecture prose → `docs/architecture.md`
- Procedures → their own doc, or a script
- Status, progress, current numbers → the plan, the gate tests, the checkpoint trailers
- Anything a routed doc already states
- Output of opencode's `/init` (commands, folder listings): cheap to rediscover, and it drifts

Numbers written into AGENTS.md go stale within a session or two and then actively mislead,
because nothing prompts anyone to update them.

## Templates

### Invariants

```markdown
## Invariants
- Never invent or interpolate measured data. → `docs/rules/measurement-invariants.md`
- Never change a governing equation without an ADR. → `docs/rules/modeling-invariants.md`
```

One line, imperative, no hedging. The paragraph, including the "instead" path, lives in the
rules file.

### Routing rows

```markdown
| `docs/rules/` | Before any code that reads, transforms, or reports measured data |
| `docs/domain/gotchas.md` | When a tool fails in a way its docs do not explain |
| `docs/reference/parameters.md` | When you need a settled parameter value |
```

"When working on this project" is not a trigger: it makes the row either always-read or
ignored. Write the situation the agent will recognise itself to be in. Sort rows by expected
read frequency.

## Budget

Cap: **2,000 tokens**. The rule that makes the cap work: **adding a line requires removing
one**. When it is genuinely full, do not raise the cap; group rows under an index doc. An extra
hop costs one read, only in the sessions that need that branch.

Do not relax the cap because tokens are cheap. The cap is what keeps this file a routing table:
the seven rules that must be obeyed should not compete with pages of things that are merely true.
