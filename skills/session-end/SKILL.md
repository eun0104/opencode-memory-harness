---
name: session-end
description: >-
  Close a working session in a project that uses the memory harness: make a final checkpoint
  the next session can start from cold, record decisions as ADRs, run the leaf's gate tests,
  propose merging a finished leaf into main, and suggest curation when due. Use when the user
  says "wrap up", "end the session", "handoff", or "let's stop here". Do not use for
  mid-session saves; that is session-checkpoint.
---

# Session End

The next session starts from `python tools/harness.py status` alone. Everything it needs must
be in the last checkpoint, the gate tests, or an ADR.

## 1. Decisions

List the choices between alternatives made this session. Each one that should outlive this
branch and has no ADR yet gets one now, in `docs/adr/` with the next number and the format of
`0001`. Record only what was said or observed.

## 2. Final checkpoint

Use `session-checkpoint`. The `Next:` line is read by a session with none of this conversation,
so it must start cold:

- Fails: `Next: continue the fitting`
- Passes: `Next: run fit_mobility.py on data/run07.csv with the T-dependent model; compare to gate test_mobility_300k`

If nothing changed since the last checkpoint but the next action did, make the commit anyway
with `--allow-empty`.

## 3. Gate tests

Run `pytest tests/gates/test_<leaf>.py -q -rxX`. If slow tests would take long, say so and ask
before running them. Report passed, xfailed, and failed counts. A FAILED or XPASS(strict)
result is a problem to fix or to put in `Next:`, never to hide.

## 4. Merge proposal

When `python tools/harness.py status` shows no open gates for the leaf and the gate tests pass:

1. Show `git log --oneline main..HEAD` and propose the merge with a one-line summary.
2. Only after the user approves, run `git switch main`, then
   `git merge --no-ff feature/<leaf> -m "Merge feature/<leaf>: <summary>"`.
3. Never squash: the checkpoint trailers are what curation harvests. Do not delete the branch
   unless the user asks.

If gates remain open, do not propose a merge; the branch carries on next session.

## 5. Curation check

Read `docs/.curation-state.json` for `last_curated_commit` if it exists. Suggest running
`context-curation` when any of these hold; suggest, do not run it:

- `git log --merges --first-parent --oneline <last_curated_commit>..main` shows 5 or more
  merges (or 5 or more merges in total when there is no state file)
- `python tools/harness.py harvest --since <last_curated_commit> --keys Learned` shows 3 or
  more lines
- AGENTS.md has grown noticeably past its budget line
- The user had to re-explain something the agent should have known

## 6. Stop cleanly

Mark every open todo completed or cancelled. Report in three lines: what was done, the `Next:`
line, and whether the leaf was merged. Never push.
