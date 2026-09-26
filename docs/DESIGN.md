# opencode-memory-harness — Design

Status: v3.1 draft, branch `v3-harness`. This document is the design contract for the rewrite.
It replaces the dependency on the external `session-context-init` and `session-handoff` skills.

v3.0 kept session state in prose files (WORKING.md, SESSION-LOG.md). v3.1 moves that state into
Git history, strict xfail tests, and ADRs, following the user's proposal. Prose written by the
agent about its own progress can claim "done"; a test either passes or does not, and a commit is
tied to the code it changed.

## Problem

- One opencode session has a 200k-token window. Auto-compaction fires at about 70% and the
  earliest context (goals, rationale, rejected alternatives) is the part that gets lost.
- oh-my-openagent keeps a todo list running without pausing (a todo-continuation mechanism
  re-prompts the agent while items remain). A long todo list therefore runs inside one session
  until compaction lands in the middle of an item.
- Implementation starts after a discussion with the planning agent. That agent has already
  written the plan file under `.omo/`, and the first session's window is already heavily used
  when `session-start` runs.
- The previous harness depended on two company-internal skills that are not available here.

## Environment facts (stated by the user)

- AGENTS.md instructions are still followed after compaction.
- Internal LLM (GLM 5.2 based), corporate network, no external dependencies beyond what the
  company provides. pytest is available.
- Windows (`C:\projects`); the shell may be PowerShell.
- A pre-compaction hook was tried in the internal build and did not work.

## Principles

1. **AGENTS.md is the anchor.** It is the one layer that survives compaction, so it carries the
   recovery rule: "if you cannot recall the goal, gates, and next action, run
   `python tools/harness.py status`".
2. **State lives where it cannot drift.** Goal = branch. Gates = strict xfail tests. Next action
   and failed attempts = trailers on checkpoint commits. Decisions = ADRs. No handoff prose.
3. **Write ahead.** Commit at event boundaries (gate done, decision made, approach failed, before
   the next todo item). Never wait for "near the limit"; the agent cannot see it reliably.
4. **Use the continuation mechanism instead of fighting it.** A checkpoint is a todo item, so
   the mechanism that keeps the agent going also guarantees the checkpoint happens.
5. **Short todo lists.** At most 5 work items, then a checkpoint item. The tree lives in the plan
   and the gate tests; the session holds a few leaves (the unlazy Depth Tree idea).
6. **One fact, one home.** The planner's plan file is the canonical plan; its path is recorded
   once in AGENTS.md. Nothing copies plan text.
7. **Done means a passing test (unlazy).** A gate is closed only when its test passes and the
   xfail marker is removed in the same commit. Weakening a test or its tolerance to make it pass
   is a decision and needs an ADR, not a silent edit. Criteria that cannot be tested are closed
   with an `Evidence:` trailer carrying the observed value.
8. **Clean stops.** Before any required stop (approval boundary, end of session), mark every open
   todo completed or cancelled so the continuation mechanism does not push past the stop.
9. **Small skills.** Each session skill body stays under about 1,500 estimated tokens, because
   the skill is loaded into the same window it is trying to protect. Enforced by tests.
10. **Portable tooling.** Python standard library for harness tooling; pytest for the project's
    tests. Skill instructions do not rely on `grep`, `sed`, or other POSIX-only commands.
11. **No runtime hooks.** The harness works through AGENTS.md, skill files, Git, and one script.
    It does not rely on a pre-compaction hook or on internal compaction settings.

## Git model

- `main` plus one branch `feature/<leaf>` per plan leaf. No develop/release/hotfix branches.
- On `feature/*` the agent commits without asking: checkpoints are the mechanism that survives
  compaction, and asking each time would make them rare.
- Merging into `main` needs the user's approval. Merge with `--no-ff`, never squash: squashing
  would erase the checkpoint trailers that curation harvests.
- Never push, rebase, reset, stash, or amend. Stage literal paths only; never `git add -A` or
  `git add .` (data files and secrets must not slip in).
- Commits on `main` other than an approved merge (e.g. the initial setup) need approval.

### Checkpoint commit

```text
checkpoint: <what changed, one line>

Next: <exact next action, specific enough to start cold>
Tried: <approach> — <why it failed>
Evidence: <criterion> — <observed value or output>
Learned: [gotcha] <tool, data, or external system behaved unexpectedly>
Learned: [candidate] <fact that may deserve a permanent home>
ADR: docs/adr/NNNN-<slug>.md
```

`Next:` is required on every checkpoint. The other trailers appear only when they apply and may
repeat. The trailers are the harvest source for curation; tagged `Learned:` lines replace the
tagged session log.

## Gate tests

- Each leaf's acceptance criteria are written as tests **before** implementation, in
  `tests/gates/test_<leaf>.py` (`-` in the leaf slug becomes `_`).
- Each unmet gate is marked
  `@pytest.mark.xfail(strict=True, raises=(AssertionError, NotImplementedError), reason="gate: <criterion>")`.
  - `strict=True`: an unexpected pass fails the run, so a met gate cannot stay marked open.
  - `raises=...`: an ImportError or typo does not masquerade as "not yet met".
  - Blocked gates use `reason="blocked: <what is missing>"`.
- A leaf is done when its gate file has no `gate:` markers left and the tests pass. Gates that
  are only `blocked:` (waiting for data, hardware, another team) do not hold the leaf hostage:
  with the user's approval the leaf merges, the blocked gates stay open on `main` where status
  keeps showing them, and a new leaf takes them over when what they wait for arrives.
- Slow tests (simulations, fits) carry `@pytest.mark.slow`. Status never runs tests: the harness
  finds open gates by reading the test files statically.

## ADRs

`docs/adr/NNNN-<slug>.md`, one decision per file, statuses `proposed` / `accepted` /
`superseded by NNNN`. Each records context, the decision, alternatives considered with the
reason each was rejected, consequences, and the source (planning session, commit, data). This
replaces `docs/decisions.md` and the "do not repeat" list for anything that outlives a branch.

## Skills and tool

| Piece | When | Does |
|---|---|---|
| `session-start` | Once after planning; each session start | First run: AGENTS.md anchor, copy the tool, ADRs for the planning rationale, stop. Resume: run status; on `main`, open the next leaf's branch and write its gate tests first |
| `session-checkpoint` | During work, at event boundaries and as todo items | Checkpoint commit on the feature branch with trailers; remove the xfail marker of a gate that now passes |
| `session-end` | End of session | Final checkpoint, ADRs for decisions made, propose the merge when the leaf is done, suggest curation when due |
| `context-curation` | About every 5 merged leaves | Harvest trailers, ADRs, notepads; promote to L2; audit budgets, reachability, stale xfails |
| `tools/harness.py` | Any time; after compaction | `status`: branch, last `Next:`, `Tried:` on this branch, open gates, uncommitted paths. `harvest`: trailers since a commit |

The tool is copied into each project as `tools/harness.py` by session-start, so AGENTS.md can
name one fixed command that works without any skill loaded.

## Files

| File | Layer | Owner | Notes |
|---|---|---|---|
| `AGENTS.md` | L0 | session-start (creates), curation (tunes) | Anchor rules, plan path, routing. 2,000-token cap |
| `.omo/` plan file | L1 | planner | Canonical plan. Path recorded in AGENTS.md; pointed to, never copied |
| `tests/gates/` | L1 (via status) | session-start, session-checkpoint | Executable acceptance criteria |
| Git history | L3 | session-checkpoint, session-end | Searched through `harness.py harvest`, never read wholesale |
| `.omo/` notepads (if present) | L3 source | oh-my-openagent executor | Per-plan learnings; harvested, not duplicated |
| `docs/adr/` | L2 | all skills | Decisions and rejected alternatives |
| `docs/theory.md` | L2 | session-start (creates), session-checkpoint (rewrites), curation (audits) | Physics applied now, with checked sources. Only for theory-driven projects |
| `docs/rules/`, `docs/domain/`, `docs/reference/` | L2 | context-curation | Facts that outlive one plan |
| `docs/.curation-state.json` | — | context-curation | `last_curated_commit`, rejected candidates |

Plan lookup: the path is known exactly once, when the plan has just been written and is still in
context. session-start records it in AGENTS.md. If the path is not in context, list the `.md`
files under `.omo/` and ask the user. The `.omo/` layout is never hard-coded.

## First session after planning

The window is already heavy and the planning rationale exists only in the conversation. Do not
run opencode's `/init`: it fills AGENTS.md with facts that are cheap to rediscover from the code,
spends the L0 budget, and drifts as the code changes.

1. AGENTS.md anchor with the plan path (a few hundred tokens; the recovery anchor as soon as it
   exists). If AGENTS.md exists, add the harness section between markers.
2. Copy the tool to `tools/harness.py`.
3. ADRs for the planning rationale that is not in the plan: chosen approach, rejected
   alternatives and why, constraints the user stated.
4. Git: ask before `git init`; check whether the plan is git-ignored; propose one setup commit on
   `main` and wait for approval.
5. Close all open todos and recommend starting implementation in a fresh session. Gate tests for
   the first leaf are written at the start of that session, with the plan in front of it.

## Theory document

Projects that search, combine, and revise physical theories while implementing them keep the
applied physics in **one living file, `docs/theory.md`** (template in `session-start`).

- **Rewritten in place, not appended.** When the model changes, the checkpoint that changes the
  code rewrites the affected sections, Model overview included, so the file always reads as one
  current account. An equation that leaves the file is recorded with its old form and reason in
  an ADR first. History lives in Git and ADRs, not in the file.
- **Stable IDs.** `EQ-<id>` per equation, used by code comments, gate test names, and ADRs.
- **Every equation links forward and back:** source (`[Rn]` + location), implementation
  (`path.py::function`), verification (`path.py::test`), status.
- **Citation integrity.** An identifier (DOI, arXiv, ISBN, internal report) is written only if
  read from the source or given by the user, with `checked: pdf | user | online`. Never from
  memory: a recalled identifier is what a fabricated citation looks like. Otherwise
  `[TBD: source]`. When the file is created, AGENTS.md gains a one-line invariant for this.
- **Checked mechanically** by `docs_inventory.py`: missing fields, malformed or unchecked
  identifiers, cited-but-unlisted references, implementation or test links that do not exist,
  and open `[TBD]` links.

The file is created only when the plan applies physical theories, mechanisms, or equations.

## Division of labour with oh-my-openagent

- **Plan file**: what to do. Owned by the planner.
- **Notepads**: what the executor learns inside one plan. Raw material for curation.
- **Gate tests and branch**: where the current leaf stands. Owned by the harness.
- **Checkpoint trailers**: next action and failed attempts between commits.
- **ADRs and L2 docs**: what must outlive the plan.

## Migration status

- Done in v3.1: `session-*` skills, `tools/harness.py`, `context-curation` with its inventory,
  README (EN/KO), tests. Verified end to end on a synthetic project: setup, gates written first,
  a gate closed by strict XPASS, recovery from `status` alone, a blocked gate carried over a
  merge, and the curation inventory counting the harvest.
- Removed from v3.0: `docs/handoff/WORKING.md`, `docs/handoff/SESSION-LOG.md`,
  `docs/decisions.md`.
- Removed from v2: root `plan.md`, `HANDOFF.md`, `handoff-spec.md`, session contract blocks,
  `INSTALL.md`.
- Not yet tried: the internal GLM 5.2 agent following these skills in a real session.

## Open questions

- Whether the executing agent ticks checkboxes in the plan file. Observable in use.
- Whether opencode re-reads AGENTS.md during a session. Test: mid-session, append a visible
  rule (e.g. "end every reply with 'OK'") and see whether the next reply follows it.
- Criteria that resist testing (judging a plot, reading a paper). The `Evidence:` trailer is the
  fallback; watch whether it gets abused as a shortcut around tests.
