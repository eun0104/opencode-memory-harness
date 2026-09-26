---
name: session-start
description: >-
  Start or resume work in a project that uses the memory harness. Use at the beginning of every
  working session, and once right after the planning agent has written the project plan, to
  set up the harness. Use when the user says "start the session", "resume", "where were we",
  or "set up the harness". Do not use for saving progress mid-session (session-checkpoint) or
  for ending a session (session-end).
---

# Session Start

Pick the mode from AGENTS.md:

- AGENTS.md contains `<!-- memory-harness:start -->` → **Resume**.
- Otherwise → **First run**.

If the marker exists but `tools/harness.py` is missing, copy `scripts/harness.py` from this
skill's directory to `tools/harness.py` and continue. Do not run opencode's `/init`.

## First run

This usually runs right after planning, when the window is already heavy and the reasons behind
the plan exist only in the conversation. Read little; write in this order.

1. **Plan path.** Take it from the conversation; the plan was just written. Do not re-read the
   plan. If the path is not in context, list the `.md` files under `.omo/` and ask which one is
   the plan. If there is no plan yet, ask whether to plan first, and stop.
2. **AGENTS.md anchor.** Fill the plan path into `templates/agents-section.md` from this skill's
   directory. If AGENTS.md does not exist, create it with a one-line title and the section. If
   it exists, append the section; change nothing outside the markers.
3. **Tool.** Copy `scripts/harness.py` from this skill's directory to `tools/harness.py`.
4. **ADRs.** Copy `templates/adr-0001.md` to `docs/adr/0001-record-decisions-as-adrs.md` with
   today's date. Then write one ADR per decision from the planning conversation that the plan
   file does not already explain: approach chosen, each rejected alternative with its reason,
   constraints the user stated. Status `accepted`, source `planning session`. Record only what
   was said.
5. **Git.** If the project is not a Git work tree, say so and ask before `git init`. If the
   primary branch is not named `main`, tell the user; the harness assumes `main`. Run
   `git check-ignore -q <plan-path>`; if the plan is ignored, say it is not versioned and ask
   how to handle it. Propose one setup commit on `main` with the exact paths (AGENTS.md,
   `tools/harness.py`, `docs/adr/`) and message; commit only after approval.
6. **Stop cleanly.** Mark every open todo completed or cancelled. Tell the user setup is done
   and that implementation should start in a new session with `session-start`.

## Resume

AGENTS.md is already in context. Read as little else as possible.

1. Run `python tools/harness.py status`.
2. **On `feature/<leaf>`:** continue from `Next:`. Treat every `Tried:` line as ruled out. If
   uncommitted paths are listed, read their diff before building on them. If the gate file is
   missing, write it first (steps 3c–3e).
3. **On `main`** (no active leaf), open the next leaf:
   a. Run `git branch --list "feature/*"`. If an unmerged leaf branch exists, ask whether to
      resume it instead.
   b. Read the plan, pick the next unfinished item, and run `git switch -c feature/<leaf>`
      with a short kebab-case slug.
   c. Write `tests/gates/test_<leaf>.py` (dashes become underscores) from
      `templates/gate_test.py`: one test per acceptance criterion of that plan item, each
      assertion measurable. For a criterion that cannot be a test, name it in the first
      checkpoint's `Next:` line; it is closed later with an `Evidence:` trailer.
   d. Run `pytest tests/gates/test_<leaf>.py -q -rxX`. Every gate must report XFAIL; fix any
      ERROR or FAILED before going on.
   e. Checkpoint with `session-checkpoint`: `checkpoint: gates for <leaf>`.
4. Read only what `Next:` needs. Read an ADR when an AGENTS.md routing row calls for it.
5. Create the todo list: at most 5 work items starting from `Next:`, then one `checkpoint`
   item.
6. Report in three lines: leaf, next action, open gates. Then start the work.

## After compaction

This skill is not needed. The AGENTS.md rule sends you to `python tools/harness.py status`.
