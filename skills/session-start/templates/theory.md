# Theory — <project>

<!-- Living document: the physics this project applies NOW, as one coherent account.
     - Rewrite the affected sections in place whenever the model changes. Never append
       "Update:" paragraphs or a changelog; history lives in Git and docs/adr/.
     - Before removing or replacing an equation, write an ADR that records the old form, the
       reason, and the replacement.
     - Citation rule: write a DOI, arXiv ID, ISBN, or internal report number only if it was read
       from the source itself or given by the user in this project. Never from memory: a
       recalled identifier is what a fabricated citation looks like. Otherwise write
       [TBD: source] and list it under Open questions.
     - Record equations and locations, never copied passages of text. -->
<!-- verified: YYYY-MM-DD -->

## Model overview

<How the mechanisms fit together now: which physics dominates in which regime, how the parts
couple, and what the model deliberately leaves out. Rewrite this whenever an equation below
changes, so it never describes an older model.>

## Equations

### EQ-<id> — <name>

$$ <equation in the notation used in the code> $$

- Symbols and units: <symbol = meaning [unit]; sign and boundary conventions>
- Assumptions: <every assumption the form inherits — the part the code cannot show>
- Valid for: <regime, field / temperature / density range, dimensionality>
- Source: [R1] eq. (<n>), p. <page> <or: adapted from [R1] eq. (<n>) — <what changed>;
  or: derived here, see Derivations; or: [TBD: source]>
- Implementation: `src/<file>.py::<function>`
- Verification: `tests/gates/test_<leaf>.py::<test>` <or [TBD: verification]>
- Status: hypothesis | adopted | validated

## Coupling and known tensions

<How the equations combine (order of evaluation, shared quantities) and where their assumptions
conflict. In theory fusion the conflicts are the research content; keep them explicit.>

## Validity domain

<The intersection of the equations' ranges, with the binding constraint named. Nothing outside
it is extrapolated without saying so.>

## Parameters

| Symbol | Meaning | Unit | Role (free / fixed / derived) | Physical bounds | Source |
|---|---|---|---|---|---|

Fitted values tied to a dataset belong in `docs/reference/parameters.md`, not here.

## Identifiability

<Parameters that trade off against each other, the data that would separate them, and what is
fixed meanwhile. `none known` if none.>

## Derivations

<Project-specific steps that no single source contains, with enough detail to re-check them.
`none` if none.>

## Open questions

- <hypothesis or unresolved source, with the open or blocked gate that would settle it>

## References

- [R1] <Authors>, "<Title>," <Journal> <vol>, <pages> (<year>).
  DOI: <10.xxxx/xxxxx> — checked: <pdf | user | online> <YYYY-MM-DD>
