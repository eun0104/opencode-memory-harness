# Profile: Scientific Theory and Mechanism Modeling

Applies when code implements, combines, fits, or tests scientific theories, mechanisms, governing
equations, or derived models. Use it as soon as the plan shows that evidence; do not wait for
curation history. This is a prior, not a checklist.

## Contents

1. Scientific traceability contract
2. Theory document
3. Evidence-state boundary
4. Verification protocol
5. Project memory contract additions
6. Recommended invariants

## Scientific traceability contract

The code is neither the theory nor proof that the theory was implemented correctly. For every
accepted model claim, preserve this chain:

```text
source or explicit project derivation
  → canonical equation or claim
  → implementation location
  → verification evidence
```

Never fabricate a missing link. Mark it `[TBD: source]`, `[TBD: implementation]`, or
`[TBD: verification]` and make it a `blocked:` gate test or a proposal blocker. A citation alone is not verification, and a passing fit alone does not
identify the correct mechanism.

## Theory document

Keep the applied theory in **one living file, `docs/theory.md`**, created from the
`session-start` template. It is not a log of entries appended over time: whenever the model
changes, the affected sections are rewritten in place, the model overview included, so the file
always reads as one coherent account of the physics applied now. Replaced forms leave the file
and are recorded, with their reason, in an ADR.

Each equation keeps a stable ID (`EQ-<id>`) so code comments, gate tests, and ADRs can refer to
the same object, and carries: symbols and units, assumptions, validity range, source,
implementation (`path.py::function`), verification (`path.py::test`), and status.

### Citation integrity

A fabricated citation is worse than none: it turns a guess into apparent authority.

- Record a DOI, arXiv ID, ISBN, or internal report number **only** if it was read from the
  source itself or given by the user. Never from memory; a recalled identifier is exactly what a
  fabricated one looks like.
- Say how it was checked: `checked: pdf`, `checked: user`, or `checked: online` with the date.
- Cite the location (equation number, section, page). If the project's form differs from the
  source, write `adapted from` and state the change.
- Without a checkable identifier, write `[TBD: source]` and list it under Open questions.
- Record equations and locations, never copied passages; keep enough provenance for an
  authorized reader to recover the source.

`docs_inventory.py` checks all of this mechanically: missing fields, malformed or unchecked
identifiers, cited-but-unlisted references, and implementation or test links that do not exist.

## Evidence-state boundary

Keep these meanings separate:

| State or kind | Meaning | Durable destination |
|---|---|---|
| Hypothesis | Plausible but not established for this project | An open gate that would test it; ADR `proposed` if a choice depends on it |
| Adopted model | Deliberately selected for implementation | `docs/theory.md` + ADR |
| Validated model | Passed named analytical, numerical, or empirical checks | `docs/theory.md`, Verification naming the passing gate tests |
| Numerical approximation | Computational substitution for a scientific form | `docs/theory.md`, stated as an approximation; never disguised as theory |
| Fitted parameter | Empirical result tied to a dataset and free/fixed split | `docs/reference/parameters.md` after acceptance |
| Rejected/superseded model | Tested or replaced with a reason | ADR, with revisit condition |

Repetition across sessions is evidence of persistence, not scientific truth. Do not promote a
hypothesis to `adopted` or `validated` merely because it recurs.

## Verification protocol

Verify each link independently when changing or curating a scientific model:

1. **Source fidelity:** confirm the cited source or project derivation supports the recorded form
   and assumptions, and that its identifier was checked, not recalled. If the source is unavailable, retain the claim but mark verification pending.
2. **Mathematical integrity:** check notation, dimensions or units, signs, boundary/initial
   conditions, limiting behavior, and compatibility with mechanisms it is combined with.
3. **Implementation fidelity:** map each material term and approximation to code. Document any
   intentional computational difference and its error or applicability.
4. **Verification evidence:** prefer dimensional checks, limiting cases, conservation laws,
   analytic or published benchmarks, manufactured solutions, and controlled dataset comparisons.
   A unit test that only reproduces the current implementation is regression evidence, not model
   validation. Write each real check as a gate test named after its equation ID (for example
   `test_eq_mu_field_low_field_limit`), so the verification link is executable.
5. **Claim scope:** ensure conclusions do not exceed the intersection of the component models'
   validity domains or the range of the validation data.

When two links disagree, record the discrepancy and stop short of declaring the model verified.
Do not silently rewrite the canonical equation to match the implementation or vice versa.

## Gates and trailers for model work

Propose only what the plan justifies. For a model-centered leaf:

1. **Gate tests per equation ID** — dimensional consistency, limiting cases, conservation, and
   comparison with a named dataset within a stated tolerance. A tolerance change needs an ADR.
2. **`Evidence:` trailers** for links that cannot be automated, such as source fidelity checked
   against a paper, with the page or equation number.
3. **`Learned: [candidate] EQ-<id> ...`** for a possible durable scientific fact, so curation can
   find it by ID.
4. **ADRs** for every adopted, rejected, or superseded model choice.

Raw runs and transient numbers stay in commits and trailers. Promote only accepted results, with
dataset, method, uncertainty or fit quality, and provenance.

## Recommended invariants

- Never change a governing equation, scientific assumption, or model-validity claim silently.
- Never treat agreement with one dataset as proof that a mechanism is uniquely identified.
- Never omit units, sign conventions, or free/fixed parameter status at an interface.
- Never extrapolate beyond the recorded validity or validation domain without flagging it.
- Never convert an unavailable source or unresolved derivation into an uncited assertion.

Put only the applicable one-line invariants in AGENTS.md and route details to `docs/theory.md` or a rules
document. Every invariant needs an explicit alternative action so it can be followed rather than
worked around.
