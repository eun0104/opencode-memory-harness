# Architecture

Describes what is true **now**. Rewrite freely as the system changes — history lives
in `docs/adr/`, not here.

<!-- verified: YYYY-MM-DD -->

## Purpose
<One paragraph: what this system does and for whom.>

## Components

| Component | Responsibility | Entry point |
|---|---|---|
| `<name>` | <one line> | `<path>` |

## Data flow
<Where data enters, what transforms it in what order, where results land.
Name the actual files. A short numbered list beats a diagram in a text file.>

1. `<input>` → `<script>` → `<intermediate>`
2. ...

## Boundaries and constraints
<What this system deliberately does not do; what it depends on that it does not control.>

## Known weak points
<Places that will break under change. Cheaper to write now than to rediscover later.>
