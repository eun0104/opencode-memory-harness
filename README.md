# opencode-memory-harness

English | [한국어](README.ko.md)

Skills and one small tool that keep an opencode agent's working memory intact across context
compaction and across sessions, for projects driven by a plan from the oh-my-openagent planner.

## The problem

A session has a 200k-token window, and auto-compaction at about 70% drops the earliest context:
the goal, the reasons behind the plan, the approaches already ruled out. oh-my-openagent keeps a
todo list running without pausing, so a long list runs until compaction lands in the middle of
an item. Notes the agent writes about its own progress drift, and can claim "done" when it is
not.

## The idea

Keep state where it cannot drift, and make recovery one command.

| Question after compaction | Answered by |
|---|---|
| What am I working on? | The branch: one plan leaf = `feature/<leaf>` |
| Is it done? | Gate tests in `tests/gates/`, marked strict xfail until they pass |
| What was I about to do? | The `Next:` trailer of the last checkpoint commit |
| What already failed? | `Tried:` trailers on the branch |
| Why is it built this way? | ADRs in `docs/adr/` |

AGENTS.md, which the agent still follows after compaction, tells it to run
`python tools/harness.py status` whenever it cannot recall the goal:

```text
Branch: feature/fit-mobility  (leaf: fit-mobility, 2 commit(s) since main)
Next: implement fit() in src/mobility.py via linearization; check test_fit_run07_within_5_percent
Tried (do not repeat):
  - scipy.optimize.curve_fit — scipy is not installed and external packages are not allowed
Open gates for this leaf (2, 1 blocked) in tests/gates/test_fit_mobility.py:
  - tests/gates/test_fit_mobility.py:16 test_fit_run07_within_5_percent — gate: fit within 5%
  - tests/gates/test_fit_mobility.py:27 test_77k — blocked: 77 K data from fab
Uncommitted: none
```

Gates use `@pytest.mark.xfail(strict=True, raises=(AssertionError, NotImplementedError))`: an
unmet criterion stays XFAIL, an import error or typo fails loudly instead of passing as "not yet
met", and a gate that starts passing while still marked fails until the marker is removed.

## Pieces

| Piece | When | Does |
|---|---|---|
| `session-start` | Once after planning; each session start | First run: AGENTS.md section, tool, ADRs for the planning rationale. Later: status, open the next leaf, write its gate tests before code |
| `session-checkpoint` | During work, at every event boundary | Commit on the leaf branch with `Next:` / `Tried:` / `Evidence:` / `Learned:` / `ADR:` trailers |
| `session-end` | End of session | ADRs for decisions, final checkpoint, gate run, merge proposal, curation reminder |
| `context-curation` | About every 5 merged leaves | Harvest trailers, ADRs, and `.omo/` notepads; promote durable facts; audit AGENTS.md budget and reachability |
| `tools/harness.py` | Any time; first thing after compaction | `status`, `gates`, `harvest`. Standard library only |

The agent commits freely on `feature/*`. Merging into `main` always waits for your approval. It
never pushes, rebases, resets, stashes, or amends.

## Workflow

1. Plan with the oh-my-openagent planner until the plan file exists.
2. In the same session run `session-start`. It writes the AGENTS.md section with the plan path,
   copies the tool, records the planning rationale as ADRs, and proposes a setup commit. Then it
   stops: the session is already heavy.
3. In a new session run `session-start` again. It opens `feature/<leaf>` for the next plan item
   and writes its gate tests first.
4. Work. Checkpoints happen as todo items (at most 5 work items, then `checkpoint`), so the
   todo continuation mechanism enforces them.
5. `session-end` records decisions, runs the gates, and proposes the merge when the leaf is done.
6. Every few leaves, `/tune-docs` runs `context-curation`: proposal first, changes only after you
   approve each item.

Do not run opencode's `/init`; it fills AGENTS.md with facts that are cheap to rediscover and
drift as the code changes.

## Installation

Copy the four skill folders into opencode's skills directory, globally or per project.

```powershell
# Global (PowerShell)
$dst = "$HOME\.config\opencode\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force skills\* $dst

# Or project-local
$dst = "C:\path\to\project\.opencode\skills"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item -Recurse -Force skills\* $dst

# Optional: /tune-docs command
New-Item -ItemType Directory -Force "$HOME\.config\opencode\commands" | Out-Null
Copy-Item skills\context-curation\command\tune-docs.md "$HOME\.config\opencode\commands\"
```

Restart opencode afterwards so the skills are discovered. `session-start` copies
`tools/harness.py` into each project on its first run.

Requirements: Python 3.8+, Git, and pytest in the project. The harness tooling itself uses only
the Python standard library and makes no network requests.

## Repository layout

```text
skills/
├── session-start/        SKILL.md, scripts/harness.py, templates (AGENTS.md section, gate test, ADR 0001)
├── session-checkpoint/   SKILL.md
├── session-end/          SKILL.md
└── context-curation/     SKILL.md, scripts/docs_inventory.py, references/, templates/, command/
docs/DESIGN.md            design contract and the reasons behind it
tests/                    standard-library regression tests
```

## Validation

```bash
python -m unittest discover -s tests -v
```

The tests cover the status and harvest tool against real temporary Git repositories, the static
gate scan, the curation inventory, and the size budgets of the skills themselves: each session
skill must stay under about 1,500 tokens, because it is loaded into the window it protects.

## License

Not yet specified.
