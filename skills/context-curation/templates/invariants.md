# <Topic> Invariants

Rules that must not be violated. Each one is summarised as a single line in AGENTS.md;
this file holds the reasoning and the alternative path.

---

## INV-01: <Rule, stated as an imperative>

**Rationale:** <what damage a violation causes, and whether it is recoverable>
**Applies to:** <the situations where this is live>
**Instead:** <what to do when the rule blocks progress>
**Source:** session NNN

---

Every invariant needs an "Instead" line. A rule with no alternative path gets worked
around rather than followed, and a worked-around rule teaches that rules are advisory.
