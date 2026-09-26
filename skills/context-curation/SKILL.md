---
name: context-curation
description: >-
  Audit and restructure the persistent knowledge layer of a memory-harness project: AGENTS.md,
  ADRs in docs/adr/, and the rules / domain / reference / architecture docs under docs/. Use
  about every 5 merged leaf branches, when AGENTS.md has grown past its budget, when docs have
  gone stale, contradictory, duplicated, or unreachable, when a plan milestone closes, when
  checkpoint trailers or .omo notepads hold learnings that were never promoted, when scientific
  theories, equations, or validation evidence need traceable project memory, or when the user
  says "tune the docs", "the agent keeps forgetting X", "our docs have drifted", or "where should
  this fact live". Do NOT use for starting, checkpointing, or ending a session.
---

# Context Curation

## Where this sits

| Piece | Owns |
|---|---|
| `session-start` / `session-checkpoint` / `session-end` | Where the current leaf stands: branch, gate tests, checkpoint trailers |
| **`context-curation`** | **What must outlive a leaf**: promoted facts, ADR hygiene, AGENTS.md routing and budget |

Checkpoint trailers and `.omo/` notepads are raw material. Curation decides what becomes project
knowledge, keeps that knowledge small and reachable, and removes nothing silently.

Whatever sits in AGENTS.md is paid for on every session and survives every compaction. The goal
is never "document more": keep AGENTS.md minimal and make everything else findable when needed.

## Layers

| Layer | What | Read when | Budget |
|---|---|---|---|
| L0 | `AGENTS.md` | Every session, after every compaction | 2,000 tokens, hard |
| L1 | Plan file (path in AGENTS.md), gate tests via `harness.py status` | Session start, recovery | Planner-owned |
| L2 | `docs/adr/`, `docs/rules/`, `docs/domain/`, `docs/reference/`, `docs/architecture.md` | Only when a routing row's trigger matches | Unbounded, pointer mandatory |
| L3 | Git history (trailers), `.omo/` notepads | Searched through `harness.py harvest`, never read whole | — |

An unreachable L2 doc is worse than none: it looks maintained and is never read.

## Non-negotiables

1. **Never delete a persistent document.** Move it to `docs/archive/YYYY-MM-DD-<name>.md` with a
   note on what superseded it. Never edit an accepted ADR except its status line.
2. **One fact, one home.** State it once; point to it everywhere else.
3. **Propose, then stop** (Step 5).
4. **Cite the source of every promoted fact**: commit SHA, ADR, notepad path, or data file.
   Never promote an inference.
5. **At most 2 new L2 files per run**, not counting ADRs, the proposal, or the state file.
6. **Follow the project's conventions**: language, headings, numbering.

## Run structure

Run in a fresh session, on `main`, between leaves. Pass A (Steps 0–5) ends with a proposal and
a stop. Pass B (Steps 6–7) applies it on a curation branch, ideally in another fresh session.
If harvesting has used more than about half the window, end at Pass A regardless.

## Step 0 — Preconditions

1. Resolve `<skill-dir>` as the directory of the SKILL.md you loaded; take scripts, templates,
   and references only from there.
2. Run `python <skill-dir>/scripts/docs_inventory.py --root .`
   - `not set up` → stop; the user runs `session-start` first.
   - `incomplete` → continue, but the missing piece is a blocking proposal item.
3. Run `git status --short --branch`. If not on `main`, or uncommitted work exists, stop and ask:
   curation between leaves keeps its commits separate from leaf work.
4. Read the profiles in `references/profiles/` that match the project. A project that applies or
   combines scientific theories, mechanisms, or equations reads `scientific-modeling.md`, plus a
   more specific profile if one matches. A profile is a prior, not a checklist.

## Step 1 — Inventory

Interpret the report with `references/audit-checks.md`. Note budget, broken pointers, orphans,
duplicates, staleness, ADR problems, gate files open too long, and theory-document problems.

## Step 2 — Harvest

1. Run `python tools/harness.py harvest --since <last_curated_commit>` (omit `--since` when the
   state file has none). If the output is long, narrow with `--keys Learned,Tried` first.
2. Read the ADRs with status `proposed`, and ADRs added since the last curation.
3. Read the `.omo/` notepads of plans whose leaves were merged since the last curation.
4. Read `rejected_candidates` in `docs/.curation-state.json`. Reconsider one if it recurred, its
   evidence changed, or its `reconsider_if` is now true.

State what was read. If the harvest found no `Learned:` lines across several merges, trailers
are not being written; say so in the proposal.

## Step 3 — Classify

Apply `references/promotion-test.md`: recurrence, cost of loss, stability, non-derivability;
2 or more promotes. Promote without scoring: invariants, rejected alternatives that have no ADR
yet, external-system quirks. Reject without scoring: task progress (plan and gates), anything
already stated elsewhere (add a pointer), anything unverified.

A `Tried:` line that recurs across branches is a rejected alternative: it needs an ADR.

Route with `references/routing-table.md`. A fact about the physics applied goes into
`docs/theory.md` by rewriting the affected section in place, never as an appended note. Invariants are the only content copied into AGENTS.md:
one line each, about seven at most. When a scientific profile applies, require its source →
canonical form → implementation → verification chain; a missing link stays `[TBD]`.

## Step 4 — Structural fixes

Over budget → demote to L2 and leave a pointer. Orphan → pointer or archive. Duplicate → one
canonical home. Stale → open the code or data it describes and check; if it holds, add
`<!-- verified: YYYY-MM-DD -->`; if not, rewrite and write an ADR. A gate file open too long →
ask whether the gate is blocked, obsolete (archive via ADR), or forgotten.

Read `references/agents-md-contract.md` before touching AGENTS.md.

## Step 5 — Proposal, then STOP

1. Write `docs/_tuning-proposal.md` from `templates/tuning-proposal.md`, ordered by impact:
   blocking items, L0 budget, invariants, promotions, structure, archive. Each item carries its
   source, destination, and exact before/after text.
2. Re-read it as an adversary: re-apply the promotion test to every promotion, cut anything below
   2, check each citation says what the item claims. State how many items were cut.
3. **Mark every open todo completed or cancelled**, so automatic continuation does not carry the
   run past the approval boundary.
4. Present the proposal and wait for approval item by item. Do not commit or change any other
   file. If the user rejects an item, ask whether the underlying rule should change.

## Step 6 — Apply (after approval)

1. Confirm `main` has not moved since the proposal (`git log -1 --format=%h main`). If it moved,
   stop and show the difference.
2. `git switch -c feature/curation-YYYY-MM-DD`.
3. Apply the approved items. New docs start from `templates/`. Every new L2 doc gets a routing
   row whose trigger is a situation the agent will recognise itself to be in.
4. Write an ADR recording the restructuring (what moved, why).
5. Update `docs/.curation-state.json` from `templates/curation-state.json`: `last_curated`
   (date), `last_curated_commit` (the `main` commit the harvest ran against), `summary`,
   `l0_tokens_after`, and structured `rejected_candidates`
   (`label`, `rejected_at_commit`, `reason`, `reconsider_if`).
6. Remove `docs/_tuning-proposal.md`.
7. Commit with literal paths, in checkpoint form (`-m "checkpoint: ..." -m "Next: ..."`).

## Step 7 — Verify, then propose the merge

Re-run `docs_inventory.py` rather than asserting from memory. Re-read every changed document and
AGENTS.md in full and check nothing contradicts anything else. Then state:

- AGENTS.md tokens before → after, under budget or not
- Every new doc has an inbound pointer with a real trigger
- Nothing was copied instead of pointed to; nothing was deleted, only archived
- The state file is updated
- For a scientific profile: every accepted model claim has its full chain or an explicit `[TBD]`

Propose `git switch main` + `git merge --no-ff feature/curation-YYYY-MM-DD` and merge only after
approval. Mark every open todo completed or cancelled before waiting.

## Improvements to the harness itself

A finding may be about the harness skills rather than this project (a trailer nobody uses, a
rule that keeps being misread). Note it in proposal section G with the exact suggested edit.
Never edit the installed skills from a curation run.

## Bundled resources

| Path | Read when |
|---|---|
| `scripts/docs_inventory.py` | Steps 0 and 7 — run it, no need to read it |
| `references/audit-checks.md` | Steps 1 and 4 |
| `references/promotion-test.md` | Step 3 |
| `references/routing-table.md` | Step 3 |
| `references/agents-md-contract.md` | Before editing AGENTS.md |
| `references/profiles/*.md` | Step 0, when a profile matches |
| `templates/*` | Steps 5 and 6 |
