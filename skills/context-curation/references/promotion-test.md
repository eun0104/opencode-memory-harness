# Promotion Test

Deciding whether a harvested fact earns a permanent home.

The bias to fight is over-promotion. Everything discovered during a leaf *feels* important while
it is fresh. But each promoted fact costs attention in future sessions and becomes something that
can go stale and mislead. When genuinely unsure, do not promote: the fact stays in the commit
history and will resurface on its own if it matters.

## The four criteria

Score each candidate. **2 or more → promote.**

### 1. Recurrence
Has it come up on **two or more distinct leaf branches**, in trailers, notepads, or ADRs? Did the
user have to re-explain it, or did the agent re-derive it?

Recurrence is the strongest single signal, because it is observed rather than predicted.

### 2. Cost of loss
If forgotten, does it cause **rework or a wrong result**? "Wrong result" outranks
"inconvenience". A flag without which the output is silently wrong passes; a flag that saves
thirty seconds does not.

### 3. Stability
Will it still be true five leaves from now? If it will change soon, it is leaf state: it belongs
in a trailer or a gate, not in the persistent layer.

### 4. Non-derivability
Can the agent cheaply rediscover it by reading the code, the data, or the gate tests? Promote
what is **not** visible from the artifacts: reasons, constraints imposed from outside, things
that were tried and failed.

## Automatic promotion, no scoring needed

- **Invariants** — "never" / "must always". The cost of missing one is asymmetric.
  → `docs/rules/<topic>-invariants.md` **and** a one-line entry in AGENTS.md.
- **A rejected alternative without an ADR** — a `Tried:` line, a notepad entry, or a user remark
  like "we tried X, it failed because Y". Without an ADR, the agent proposes X again.
- **External-system quirks** — behaviour of a system the agent cannot inspect (DRM, licensed
  tools, internal APIs, lab instruments).

## Automatic rejection

- Task progress → the plan and the gate tests
- The next action or a blocker → a `Next:` trailer or a `blocked:` gate
- Anything already stated in a persistent doc → add a pointer, do not restate
- Anything inferred but not verified → not a fact yet; an open gate or an open question

## Worked examples

**Candidate:** `Learned: [gotcha] Word must already be running for the COM extractor to attach`
(on two branches).
Recurrence ✓ · Loss ✓ (script fails outright) · Stability ✓ · Non-derivable ✓
→ **Promote** to `docs/domain/gotchas.md`.

**Candidate:** `Learned: [candidate] used --watch on the budget script`
Recurrence ✗ · Loss ✗ · Stability ✓ · Non-derivable ✗ (it is in `--help`)
→ **Reject.** Score 1.

**Candidate:** `Tried: coherence-only segmentation — crosshatched stripes land in the wrong class`
(two branches, no ADR).
→ **Promote without scoring** as an ADR: rejected alternative.

**Candidate:** "The vision model must never compute the final measured ratio directly."
→ **Promote** immediately as an invariant. Rules file + one AGENTS.md line.

**Candidate:** `Evidence: abstract is 7 words over the limit`
Recurrence ✗ · Loss ✗ (a script measures it) · Stability ✗ · Non-derivable ✗
→ **Reject.** Leaf state, not project knowledge.
