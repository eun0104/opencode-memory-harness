---
name: session-checkpoint
description: >-
  Save progress as a checkpoint commit on the current feature branch so it survives context
  compaction. Use at every event boundary during work: after a gate test passes or fails, after
  a decision between alternatives, after an approach fails, before starting the next todo item,
  before a large read or a long run, and whenever a todo item named "checkpoint" comes up. Also
  use when the user says "checkpoint" or "save progress". Do not use for end-of-session wrap-up;
  that is session-end.
---

# Session Checkpoint

Compaction can happen at any moment. A checkpoint commit is what survives: the code, the gate
tests, and trailers saying what comes next and what already failed. It costs one commit; a
missed one costs the reasoning since the last one. Do not wait until the context feels full.

## When

- A gate passed, failed, or turned out to be blocked
- A decision was made between alternatives
- An approach failed
- Before starting the next todo item, a large read, or a long run
- A todo item named `checkpoint` is next

## Todo list rule

When you create or extend a todo list, put at most 5 work items in it, followed by one item
named `checkpoint`. After the checkpoint, take the next items from `Next:` and the open gates.

## How

1. **Branch.** Run `git rev-parse --abbrev-ref HEAD`. If it is not `feature/<leaf>`, do not
   commit; tell the user that work belongs on a leaf branch opened by `session-start`.
2. **Closed gates.** For each gate you believe passes, run it:
   `pytest "tests/gates/test_<leaf>.py::<test_name>" -q`. While the marker is on, a met gate
   is reported as `FAILED ... [XPASS(strict)]`: that means the criterion is met. Remove its
   xfail marker and run it again; it must now pass. Plain `XFAIL` means not met yet. If
   passing required changing its assertion or tolerance, write an ADR first.
3. **Decisions.** For a choice between alternatives that should outlive this branch, write an
   ADR in `docs/adr/` with the next number, following the format of `0001`.
4. **Theory.** If this checkpoint adds or changes a physical equation, assumption, parameter
   role, or validity range in code, update `docs/theory.md` in the same commit. Rewrite the
   affected sections in place, Model overview included, so the file stays one current account;
   never append update notes. Replacing or removing an equation needs an ADR first that records
   the old form. For sources, follow the citation rule in the file's header: an identifier only
   if read from the source or given by the user, with `checked:`; otherwise `[TBD: source]`.
   If the file does not exist yet, create it as `session-start` First run step 5 describes.
5. **Stage.** From `git status --short`, pick the files that belong to this work and run
   `git add -- <path> <path> ...`. Never stage generated data, large outputs, or credentials.
   Never `git add -A` or `git add .`.
6. **Commit.** Pass each line as its own `-m` argument:

   ```text
   git commit -m "checkpoint: <what changed, one line>" -m "Next: <exact next action>" -m "Tried: <approach> — <why it failed>"
   ```

   | Trailer | Rule |
   |---|---|
   | `Next:` | Required. Specific enough to start cold: file, command, input, and what to compare |
   | `Tried:` | Each approach that failed since the last checkpoint, with the reason |
   | `Evidence:` | A criterion that cannot be a test, closed with the observed value or output |
   | `Learned:` | Tagged `[gotcha]` (tool, data, or system behaved unexpectedly) or `[candidate]` (fact that may deserve a permanent home) |
   | `ADR:` | Path of an ADR written in this checkpoint |

   In PowerShell, avoid `$` and backticks inside the double quotes.
7. **Continue.** Do not stop the work for a checkpoint. Go on with `Next:`.

## Do not

- Commit on `main`, amend, rebase, reset, stash, or push.
- Write narrative. Trailers are state: next action, failed attempts, evidence.
- Close a gate by editing the test instead of the code, unless an ADR records why.
- Repeat an old `Tried:` line; earlier ones stay in the branch history and `status` shows them.
