<!-- memory-harness:start -->
## Memory rules

<!-- L0 budget: 2,000 tokens for this whole file. Adding a line requires removing one. -->

- Plan: `<plan-path>` — owned by the planner. Point to it; never copy it.
- State lives in Git and tests, not in notes. If you cannot recall the current goal, gates, and
  next action (for example after compaction), run `python tools/harness.py status` before
  anything else and continue from its `Next:` line. Its `Tried:` lines must not be repeated.
- One plan leaf = one branch `feature/<leaf>`. Its acceptance criteria are tests in
  `tests/gates/test_<leaf>.py`, written before the code, each marked
  `@pytest.mark.xfail(strict=True, raises=(AssertionError, NotImplementedError), reason="gate: ...")`.
- A gate is closed only when its test passes and its xfail marker is removed in the same commit.
  Never loosen an assertion or tolerance to make a gate pass without an ADR.
- Checkpoint with the `session-checkpoint` skill after each gate, each decision, each failed
  approach, and before the next todo item.
- A todo list holds at most 5 work items followed by one `checkpoint` item.
- Commit freely on `feature/*`. Merging into `main` needs the user's approval. Never push,
  rebase, reset, stash, or amend. Stage literal paths only.
- Before any required stop (waiting for approval, end of session), mark every open todo
  completed or cancelled.
- Start a session with `session-start`; end it with `session-end`.

| Read this | When |
|---|---|
| `docs/adr/` | Before proposing an approach that changes a design choice or revisits a rejected alternative |
| `python tools/harness.py harvest` | When you need what earlier sessions learned; never read Git history wholesale |
| skill `context-curation` | About every 5 merged leaves, when this file exceeds its budget, or when a fact keeps being re-explained |
<!-- memory-harness:end -->
