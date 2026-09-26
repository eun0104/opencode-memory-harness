# Profile: Physics-Based Device Modeling & Data Fitting

Applies to projects that build transport or device models from physical theory, fit them to
measured data, and combine mechanisms from different theoretical frameworks.

Apply this together with `scientific-modeling.md`. Its traceability chain, evidence states, and
verification protocol remain mandatory; this profile adds device-modeling and fitting details.

A profile is a **prior, not a checklist**. Confirm each item against what the plan, commits, and ADRs
actually show before creating anything.

## Contents

1. What makes this project class distinctive
2. Recommended L2 documents
3. Recommended invariants
4. Recommended gate tests
5. What NOT to promote

## What makes this project class distinctive

The code is not the model. A line like

```python
mu = mu0 / (1 + (E / Ec)**beta)
```

carries assumptions — steady state, spatially uniform field, a particular scattering hierarchy,
a carrier statistics regime — and **none of them are visible in the code**. This is the core
problem: the persistent knowledge here is precisely the part that cannot be recovered by reading
the implementation.

It gets sharper when mechanisms from different frameworks are combined. Each is valid in its own
limit; the composite is valid only in the **intersection**, which is narrower than any component
and which nothing in the codebase records. An agent picking up such a model in a later session
will extend it into regimes where it is meaningless, and the output will look completely normal.

## Recommended L2 documents

### `docs/theory.md` — the highest-value doc for this project class

The single living theory document from `scientific-modeling.md`, rewritten in place as the model
changes. For device modeling, these sections carry the most weight:

- **Assumptions** per equation: every one inherited (steady state, carrier statistics regime,
  scattering hierarchy). This is the part the code cannot tell you.
- **Coupling and known tensions**: where mechanisms from different frameworks conflict. In
  creative theory fusion the conflicts are the research content, and they are the first thing
  lost between sessions.
- **Validity domain**: the intersection of the component ranges, with the binding constraint
  named. It is what an agent needs before it agrees to extrapolate anything.
- **Identifiability**: which parameters trade off, what data would separate them, and what is
  fixed meanwhile. For example: N_t and E_t degenerate in room-temperature I-V alone; breaks
  with temperature-dependent data; until then E_t is fixed at a sourced value and N_t reported
  as conditional on it.

Sources follow the citation-integrity rules: identifiers only from the paper or the user, with
how they were checked.

### `docs/reference/parameters.md`

Extend the standard reference template with columns this work requires:

| Parameter | Value | Unit | Free/Fixed | Fitted against | Model version | Fit quality | Source |
|---|---|---|---|---|---|---|---|

A fitted value without its dataset and its free/fixed status is not a result — it is a number.
Values silently migrating from one device's fit into another's initial guess is a routine and
hard-to-detect failure.

### `docs/domain/gotchas.md`

Include **numerical** gotchas alongside tool ones. Distinguishing a convergence artefact from a
physical result is a recurring judgement here, and getting it wrong in either direction wastes a
session — chasing physics that is a solver artefact, or dismissing real physics as one.

### ADRs in `docs/adr/`

Physics choices are ADRs. `Revisit if` maps naturally onto data conditions:
*"Revisit if we obtain low-temperature data below 100 K"* — the decision was made under a data
constraint, and should reopen when the constraint lifts.

## Recommended invariants

For `docs/rules/modeling-invariants.md`, with one-line summaries in AGENTS.md:

- **Never change a governing equation silently.** In this work the model *is* the contribution. An unannounced change to a functional form is an undocumented change to the research result. Propose it as an ADR.
- **Never report a fit without stating which parameters were free and which were fixed.** Same number, entirely different claim.
- **Never extrapolate outside the stated validity domain without flagging it.** The model will return a number regardless; nothing in the output signals that it is meaningless.
- **Never invent, interpolate, or extend measured data.** Fabricated data can reach a publication and is unrecoverable.
- **State units and sign conventions at every interface.** Silent factor errors from cm/m, eV/J, or gate-voltage sign survive for many sessions because the shape of the curve still looks plausible.

Every invariant needs its "Instead" line: what to do when the rule blocks progress. A rule with
no alternative path gets worked around rather than followed.

## Recommended gate tests

Write these per leaf, before the code, where the plan item supports them:

1. **Units and dimensions** — every interface function returns the documented units; a cm/m or
   eV/J slip fails a test instead of surviving as a plausible-looking curve.
2. **Limiting cases** — e.g. field-dependent mobility tends to `mu0` as E → 0; temperature
   dependence reduces to the known form in its regime.
3. **Fit quality on a named dataset** — residual metric within a stated tolerance, with the
   free/fixed parameter split asserted, not just the final values.
4. **Physical bounds** — fitted parameters inside physically meaningful ranges.

Residual structure is the signal that drives the next hypothesis, and it cannot be a test. Write
what it suggests is missing in the checkpoint that records the fit, as
`Evidence: <dataset> residual shows <pattern>` and, if it points to a new mechanism,
`Learned: [candidate] ...`. It is obvious while looking at the plot and gone by the next session.

## What NOT to promote

- Individual fit runs and their numbers → commits and trailers; only *accepted* values reach `reference/`
- Plot styling, file paths for one figure → not project knowledge
- Anything derivable by running the code and looking → the code is its own documentation
- A physical intuition not yet tested against data → an open gate that would test it, not a domain doc. Promoting an untested intuition into the persistent layer converts a hypothesis into an assumption without anyone deciding to.
