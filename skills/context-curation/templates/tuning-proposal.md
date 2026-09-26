# Doc Tuning Proposal — <YYYY-MM-DD>

**Harvested:** `<last_curated_commit or "whole history">`..`<main HEAD>` · <N> merges ·
<N> trailer lines · <N> notepad files
**Last curated:** <date or "never">
**AGENTS.md:** ~<N> tokens → ~<N> tokens after this proposal
**Git:** on `main` @ `<sha>`, working tree clean

## Summary

<Two or three sentences: the main problem with the knowledge layer now, and what this proposal
does about it.>

---

## A. Blocking — apply first

Setup repairs from the inventory (`incomplete` mode), broken pointers, ADR number clashes.

### A1. <Short title>
- **Finding:** <what the audit found>
- **Impact:** <what goes wrong if untouched>
- **Change:** <exact edit>
- **Files:** `<path>` <created | edited | archived>

---

## B. Promotions

### B1. <the fact, in one sentence>
- **Source:** <commit SHA + trailer line, ADR path, or notepad path>
- **Test:** recurrence ✓ · loss ✓ · stability ✓ · non-derivable ✗ → **3/4, promote**
- **Scientific traceability, when applicable:** <evidence state> · <source or derivation> →
  <canonical equation/claim ID> → <implementation> → <gate test or evidence>; `[TBD]` for gaps
- **Destination:** `docs/domain/gotchas.md` (new section) <or `docs/adr/NNNN-<slug>.md`>
- **AGENTS.md:** row exists / add row: `| docs/domain/gotchas.md | when a tool fails unexpectedly |`
- **Draft:**
  ```markdown
  <the exact text to be inserted>
  ```

---

## C. Structural changes

### C1. <e.g. Demote setup procedure out of AGENTS.md>
- **Before:** <lines 34–58 of AGENTS.md, ~400 tokens>
- **After:** moved to `docs/setup.md`; AGENTS.md keeps one routing row
- **Net L0 change:** −380 tokens

---

## D. Archive

| File | Reason | Superseded by |
|---|---|---|
| `docs/domain/old-model.md` | model replaced | `docs/adr/0009-drift-diffusion.md` |

---

## E. Considered, not promoted

Recorded so the question is not re-litigated unchanged. Reopen when evidence changes or
`Reconsider if` becomes true.

| Candidate | Score | Why not | Reconsider if |
|---|---|---|---|
| <fact> | 1/4 | derivable from `--help`; one branch only | it recurs on another leaf |

---

## F. Open gates and ADR hygiene

| Item | Finding | Proposed |
|---|---|---|
| `tests/gates/test_fit_77k.py` | open 140 days | mark `blocked: 77 K data` / archive via ADR / add to plan |
| `docs/adr/0004-...md` | `proposed` since <date> | ask the user to accept or supersede |

---

## G. Noted for the harness skills — NOT APPLIED

Observations about `session-*` or `context-curation` themselves. **Nothing here is applied by
the tuning run.** Empty is the normal outcome.

### G1. <observation>
- **Seen here as:** <what happened, with commits or branches>
- **Why it may generalize:** <reason it is not project-specific>
- **Suggested edit:** <exact line or change>

---

## Open questions for the user

1. <anything the agent could not decide alone — especially archiving anything the user may read
   by hand>
