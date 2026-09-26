# Audit Checks

How to read `docs_inventory.py` output and what to do about each finding. Fix in this order;
earlier findings change the shape of later ones.

## Contents

0. Setup mode
1. L0 over budget
2. Broken pointers
3. Unreachable documents
4. Duplicated passages
5. Stale documents
6. ADR problems
7. Harvest sources
8. Gate files open too long
9. Theory document

## 0. Setup mode

- `not set up`: AGENTS.md has no `<!-- memory-harness:start -->` section. Curation has nothing to
  curate yet. Stop and let the user run `session-start`. Do not create the section yourself.
- `incomplete`: the section exists, but the `- Plan:` line, the plan file, or `tools/harness.py`
  is missing. Make the repair a blocking proposal item: a missing tool is copied from the
  `session-start` skill; a missing plan needs the user to say where the plan is.
- A git-ignored plan is not versioned. Report it; the user decides whether to track it.

## 1. L0 over budget

**Report:** `AGENTS.md: 3,180 tokens (budget 2,000) - OVER by 1,180`

The cost is signal, not tokens: invariants stop reading as invariants once they sit among
paragraphs that are merely informative. Demote in this order until it fits:

1. Rationale and history → an ADR.
2. Procedures → their own doc, or a script.
3. Lists longer than about seven items → a reference table.
4. Duplicated content → a pointer.
5. Domain background → `docs/domain/`.

Never demote the memory rules inside the harness section, the plan line, the invariant
one-liners, or the routing table. If it still does not fit, group related routing rows under
one index doc.

## 2. Broken pointers

**Report:** `AGENTS.md -> docs/domain/gotchas.md (target missing)`

The most damaging finding: the agent believes it consulted a doc that is not there. Correct the
path, create the doc from a template, or remove the pointer. A backticked `docs/<dir>/` pointer
to a missing directory is broken too.

## 3. Unreachable documents

**Report:** `docs/domain/sb-growth.md` under "Unreachable from AGENTS.md"

Reachability follows Markdown links, backticked `.md` paths, and backticked `docs/<dir>/`
pointers (which reach every doc inside) from AGENTS.md. Resolutions:

- Still relevant → add a routing row with a real trigger.
- Superseded → archive with a `superseded by` note.
- Never used → archive.

Ask before archiving: an orphan is often a doc the user reads by hand.

## 4. Duplicated passages

**Report:** `AGENTS.md para 4 ~ docs/architecture.md para 2 (similarity 0.71)`

Duplication guarantees contradiction, because only one copy gets updated. Pick the canonical
home with the routing table and replace the other with a pointer. Check whether the copies
already disagree; if so, report which one has been guiding sessions. Below about 0.5, a short
summary pointing to a full treatment is usually the intended pattern.

## 5. Stale documents

**Report:** `docs/architecture.md - 118 days (threshold 90)`

A suspicion, not a verdict. Open the code or data the doc describes and check it yourself rather
than asking the user. If it holds, add or replace `<!-- verified: YYYY-MM-DD -->`; the marker
resets the clock and ages like any date. If it drifted, rewrite it and write an ADR for what
changed. ADRs are exempt: they record a decision at a point in time.

For a scientific model document the code is not the authority. Verify source, canonical form,
implementation mapping, and verification evidence separately (`profiles/scientific-modeling.md`).

Stale invariants deserve extra care: a rule everyone quietly stopped following teaches the agent
that rules are advisory.

## 6. ADR problems

- Missing `- Status:` or `- Source:` line → fix the header only; never rewrite an accepted body.
- Two ADRs with one number → renumber the newer one and fix pointers to it.
- A name not in `NNNN-<slug>.md` form → rename it.
- `proposed` ADRs that were never decided → ask the user to accept or reject; a rejected one
  becomes `superseded by NNNN` or is archived.

## 7. Harvest sources

The report counts merges and trailers since `last_curated_commit`, broken down by `Learned:`
tag, and lists `.omo/` notepads. Read the material with `python tools/harness.py harvest`.

- Many merges but no `Learned:` lines → trailers are not being written. Say so; the fix is
  usually a clearer example in the checkpoint skill (proposal section G), not a new rule.
- `last_curated_commit` not found (history rewritten) → harvest the whole history once and
  record the new commit.

## 8. Gate files open too long

**Report:** `tests/gates/test_fit_77k.py - 1 open marker(s), last commit 140 days ago`

An xfail that stays open is either blocked, obsolete, or forgotten. Ask which:

- Blocked → its reason should read `blocked: <what is missing>`.
- Obsolete (the plan changed) → record the change in an ADR, then archive the test.
- Forgotten → it belongs in the plan as unfinished work.

Never delete an open gate silently: it is a claim the project has not met yet.

## 9. Theory document

**Report:** `[R2]: identifier without 'checked: pdf | user | online'`

`docs/theory.md` is only trustworthy if every link in it holds. Fix problems in this order:

- **Unchecked or malformed identifier** → ask the user for the source, or read it from the PDF
  they provide. Never "fix" a DOI from memory; if it cannot be checked, replace it with
  `[TBD: source]`. A plausible-looking identifier nobody checked is the failure this file exists
  to prevent.
- **Implementation or Verification link not found** → the code moved or was renamed; update the
  link, or mark `[TBD: verification]` if the test is gone.
- **Cited but not listed / listed but never cited** → add the entry or remove the stray one.
- **Missing fields** → add them; write `[TBD: ...]` rather than guessing.

Then read the file whole. It must read as one account of the current model: an overview that
describes an older model, or paragraphs that read like appended update notes, mean it needs a
rewrite in place, with an ADR for any form that left the file.
