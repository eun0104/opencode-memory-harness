# Usage Guide

English | [한국어](USAGE.ko.md)

How to install the harness and use it on a real project with opencode + oh-my-openagent, one
scenario at a time. Every example output below was produced by running this repository's tools.

## Contents

1. [At a glance](#1-at-a-glance)
2. [Install and check](#2-install-and-check)
3. [Scenario 1 — New project: set up right after planning](#3-scenario-1--new-project-set-up-right-after-planning)
4. [Scenario 2 — Start implementing: open the first leaf in a new session](#4-scenario-2--start-implementing-open-the-first-leaf-in-a-new-session)
5. [Scenario 3 — While working: checkpoints and compaction](#5-scenario-3--while-working-checkpoints-and-compaction)
6. [Scenario 4 — Adding or changing physics, backed by papers](#6-scenario-4--adding-or-changing-physics-backed-by-papers)
7. [Scenario 5 — Ending a session and merging](#7-scenario-5--ending-a-session-and-merging)
8. [Scenario 6 — A criterion blocked by something external](#8-scenario-6--a-criterion-blocked-by-something-external)
9. [Scenario 7 — Periodic curation](#9-scenario-7--periodic-curation)
10. [Scenario 8 — Coming back after days away; checking state yourself](#10-scenario-8--coming-back-after-days-away-checking-state-yourself)
11. [Scenario 9 — Adopting the harness in an existing project](#11-scenario-9--adopting-the-harness-in-an-existing-project)
12. [What needs your approval](#12-what-needs-your-approval)
13. [Updating the harness](#13-updating-the-harness)
14. [Troubleshooting](#14-troubleshooting)

## 1. At a glance

```text
[planning session]   plan with Prometheus → plan file under .omo/
                     session-start (first run) → AGENTS.md section, tools/harness.py, ADRs, (theory)
                     → approve the setup commit → end the session
[working sessions]   session-start → branch feature/<leaf> → gate tests first → work
                     ↳ checkpoint commits (after compaction, one status command recovers)
                     session-end → record decisions, run gates, propose merging into main if done
[every ~5 leaves]    /tune-docs → proposal → approve item by item → apply
```

| Question | Where the answer lives |
|---|---|
| What did we decide to do? | The plan file under `.omo/` (its path is one line in AGENTS.md) |
| What am I working on? | The branch name `feature/<leaf>` |
| Is it done? | Gate tests in `tests/gates/test_<leaf>.py` |
| What was I about to do? | The `Next:` line of the last checkpoint commit |
| What already failed? | `Tried:` lines on the branch |
| Why is it built this way? | ADRs in `docs/adr/` |
| Which physics are we applying? | `docs/theory.md` |

## 2. Install and check

### Copy the skills

Per-project installation is recommended: the skill version is pinned with the project, and if
you commit it, the project records which rules it was built under.

```powershell
# Where you keep the harness repository
cd C:\projects\opencode-memory-harness
git pull

# Install into a project
$proj = "C:\projects\my-device-model"
New-Item -ItemType Directory -Force "$proj\.opencode\skills" | Out-Null
Copy-Item -Recurse -Force skills\* "$proj\.opencode\skills\"

# Optional: the /tune-docs command
New-Item -ItemType Directory -Force "$proj\.opencode\commands" | Out-Null
Copy-Item -Force skills\context-curation\command\tune-docs.md "$proj\.opencode\commands\"
```

Resulting layout:

```text
my-device-model\
└── .opencode\
    ├── skills\
    │   ├── session-start\SKILL.md
    │   ├── session-checkpoint\SKILL.md
    │   ├── session-end\SKILL.md
    │   └── context-curation\SKILL.md
    └── commands\tune-docs.md
```

To use one version everywhere, copy into `$HOME\.config\opencode\skills\` instead. If both
exist, the per-project copy is the intended override; keeping only one avoids confusion.

### Requirements

- Python 3.8 or newer (tested on 3.8 to 3.13)
- Git
- pytest in the project's environment, for gate tests. The harness tooling itself uses only
  the standard library.

### Check

Open opencode in the project folder and ask:

```text
List the skills you can use.
```

You should see `session-start`, `session-checkpoint`, `session-end`, and `context-curation`.
If not, see [Troubleshooting](#14-troubleshooting).

## 3. Scenario 1 — New project: set up right after planning

**When:** right after Prometheus (the planning agent) has written the plan file, **in the same
session**.

The reasons behind the plan (what was chosen, what was rejected, and why) exist only in the
planning conversation. This step moves them into files before the session closes.

**Type:**

```text
Set up the harness with the session-start skill.
```

**What the agent does:**

1. Takes the plan path from the conversation (it does not re-read the plan).
2. Writes the harness section into AGENTS.md: memory rules and the plan path. This is the
   recovery anchor that survives compaction. If AGENTS.md exists, it only appends between
   markers.
3. Copies `tools/harness.py`.
4. Writes `docs/adr/0001-record-decisions-as-adrs.md` and one ADR per decision from the planning
   conversation: the approach chosen, rejected alternatives with reasons, constraints you stated.
5. If the plan applies physical theories or equations, creates `docs/theory.md` and adds a
   one-line citation rule to AGENTS.md (see [Scenario 4](#6-scenario-4--adding-or-changing-physics-backed-by-papers)).
6. Checks Git: asks before `git init` if needed, tells you if the plan file is git-ignored, and
   adds `__pycache__/` and `.pytest_cache/` to `.gitignore`.
7. Proposes a setup commit on `main`, showing the exact paths and message, and **waits for your
   approval**.
8. Closes all todos, tells you to start implementation in a new session, and stops.

**You approve:** `git init` (when needed), and the setup commit's paths and message.

**Result:**

```text
AGENTS.md                              ← harness section (about 500 tokens)
tools/harness.py
docs/adr/0001-record-decisions-as-adrs.md
docs/adr/0002-....md                   ← planning rationale
docs/theory.md                         ← only for theory-driven projects
.gitignore
```

**Close the session here.** The planning session is already heavy.

> Do not run opencode's `/init`. It fills AGENTS.md with facts that are cheap to rediscover from
> the code and drift as the code changes.

## 4. Scenario 2 — Start implementing: open the first leaf in a new session

**When:** the first session after setup, or a new session after merging the previous leaf.

**Type:**

```text
Run session-start.
```

**What the agent does:**

1. Runs `python tools/harness.py status`. On `main` there is no active leaf:

   ```text
   Branch: main
   Uncommitted: none
   Note: on 'main', not a feature/* branch: no active leaf
   ```

2. If an unmerged `feature/*` branch exists, asks whether to resume it.
3. Reads the plan, picks the next item, and opens `git switch -c feature/fit-mobility`. Branch
   names are lowercase ASCII with dashes.
4. **Before any code**, writes the acceptance criteria as tests in
   `tests/gates/test_fit_mobility.py`:

   ```python
   import pytest

   GATE = dict(strict=True, raises=(AssertionError, NotImplementedError))


   @pytest.mark.xfail(**GATE, reason="gate: low-field limit equals mu0")
   def test_low_field_limit():
       from src.mobility import mu
       assert abs(mu(1e-9, mu0=1400.0, Ec=18.0) - 1400.0) < 1e-6


   @pytest.mark.xfail(**GATE, reason="gate: fit to data/run07.csv within 5% at every point")
   def test_fit_run07_within_5_percent():
       raise NotImplementedError


   @pytest.mark.xfail(strict=True, reason="blocked: 77 K data from fab")
   def test_77k():
       raise NotImplementedError
   ```

5. Confirms every gate reports XFAIL:

   ```text
   XFAIL tests/gates/test_fit_mobility.py::test_low_field_limit - gate: low-field limit equals mu0
   XFAIL tests/gates/test_fit_mobility.py::test_fit_run07_within_5_percent - gate: fit to data/run07.csv within 5% at every point
   XFAIL tests/gates/test_fit_mobility.py::test_77k - blocked: 77 K data from fab
   3 xfailed in 0.02s
   ```

6. Commits `checkpoint: gates for fit-mobility`, builds a todo list (at most 5 work items plus
   `checkpoint`), reports leaf, next action, and open gates in three lines, and starts working.

**Your part: review the gate tests.** This file is the definition of "done". Checking the
tolerances and looking for missing criteria here is worth more than any later review. Loosening
a criterion afterwards requires the agent to write an ADR first.

## 5. Scenario 3 — While working: checkpoints and compaction

### Checkpoints

The agent commits a checkpoint on the feature branch at every event: a gate passes, a choice is
made between alternatives, an approach fails, or the next todo item starts. It commits without
asking; this is what survives compaction.

```text
checkpoint: mu(E) implemented, low-field gate closed

Next: implement fit() in src/mobility.py by linear least squares on 1/mu = 1/mu0 + E/(mu0*Ec); run test_fit_run07_within_5_percent

Tried: scipy.optimize.curve_fit — scipy is not available on the internal network

Learned: [gotcha] run07.csv mobility column is in cm2/Vs, not m2/Vs
```

| Line | Meaning |
|---|---|
| `Next:` | The next action, specific enough to start with no context (required) |
| `Tried:` | An approach that failed, and why. Not to be repeated |
| `Evidence:` | The observed value that closes a criterion that cannot be a test |
| `Learned:` | `[gotcha]` unexpected behaviour, `[candidate]` fact that may deserve a permanent home |
| `ADR:` | Path of an ADR written in this checkpoint |

To ask for one explicitly:

```text
Make a checkpoint.
```

### How a gate closes

When the code meets a criterion while its xfail marker is still on, strict mode makes the test
fail:

```text
FAILED tests/gates/test_fit_mobility.py::test_low_field_limit - [XPASS(strict...
```

Here FAILED means "the criterion is met; remove the marker". The agent removes it, reruns the
test to see it pass, and commits both together. It cannot claim "done" without meeting the
criterion, and it cannot leave a met criterion marked open. Thanks to `raises=`, a typo or an
import error shows up as FAILED instead of hiding as "not yet met".

### When compaction happens

Following the AGENTS.md rule, the agent checks state first whenever it cannot recall the goal:

```text
Branch: feature/fit-mobility  (leaf: fit-mobility, 2 commit(s) since main)
Next: implement fit() in src/mobility.py by linear least squares on 1/mu = 1/mu0 + E/(mu0*Ec); run test_fit_run07_within_5_percent
  from 956a661e18 "checkpoint: mu(E) implemented, low-field gate closed"
Tried (do not repeat):
  - scipy.optimize.curve_fit — scipy is not available on the internal network
Open gates for this leaf (2, 1 blocked) in tests/gates/test_fit_mobility.py:
  - tests/gates/test_fit_mobility.py:12 test_fit_run07_within_5_percent — gate: fit to data/run07.csv within 5% at every point
  - tests/gates/test_fit_mobility.py:17 test_77k — blocked: 77 K data from fab
Uncommitted: none
```

If after compaction the agent seems lost or retries something that already failed, type:

```text
Run python tools/harness.py status and continue from Next. Do not use anything listed under Tried.
```

## 6. Scenario 4 — Adding or changing physics, backed by papers

`docs/theory.md` is **one living document** of the physics applied now. When the model changes,
the checkpoint that changes the code rewrites the affected sections in place. Nothing is appended
as "Update:" notes, so it always reads as one account of the current model.

### Adding a mechanism

Give the paper as a PDF whenever possible:

```text
Add eq. (8) of the attached paper to the mobility model. It adds the temperature dependence.
```

Together with the implementation, the same checkpoint updates `docs/theory.md`:

```markdown
### EQ-mu-T — temperature scaling of mu0

$$ \mu_0(T) = \mu_0(300) (T/300)^{-\alpha} $$

- Symbols and units: T [K], alpha dimensionless
- Assumptions: phonon-limited scattering dominates
- Valid for: 200–400 K
- Source: [R2] eq. (8), p. 12
- Implementation: `src/mobility.py::mu0_of_T`
- Verification: `tests/gates/test_mu_temperature.py::test_eq_mu_t_300k_limit`
- Status: adopted

## References

- [R2] <Authors>, "<Title>," <Journal> <vol>, <pages> (<year>).
  DOI: <DOI read from the PDF> — checked: pdf 2026-09-27
```

### Citation rule (against fabricated sources)

- A DOI, arXiv ID, ISBN, or internal report number is written **only if read from the source or
  given by you**. Never from memory: a plausible-looking remembered DOI is exactly what a
  fabricated citation looks like.
- How it was checked is recorded: `checked: pdf`, `checked: user`, or `checked: online`.
- If it cannot be checked, the entry says `[TBD: source]` and goes under Open questions. Give the
  DOI later and it is filled in as `checked: user`:

```text
The DOI of R2 is 10.xxxx/xxxxx. Fill it in.
```

On an internal network most entries will be `checked: pdf` or `checked: user`.

### Replacing or removing an equation

The agent first writes an ADR recording the old form and the reason, then rewrites
`docs/theory.md` in place. The old equation leaves the theory document but stays in the ADR and
in Git history.

### Automatic checks

The curation inventory (`docs_inventory.py`) checks the theory document mechanically: each
equation has source, implementation, and verification; identifiers are well formed and carry how
they were checked; cited references are listed; and the named functions and tests exist. For a
document pointing to a function not yet written and a DOI with no check recorded, it reports:

```text
## 8. Theory document

`docs/theory.md`: 2 equation(s), 2 reference(s).

**Problems (fix before trusting the document):**
- EQ-mu-T: Implementation `src/mobility.py::mu0_of_T` not defined in that file
- [R2]: identifier without 'checked: pdf | user | online'

Open `[TBD]` links: EQ-mu-T: valid for; EQ-mu-T: verification.
```

## 7. Scenario 5 — Ending a session and merging

**Type:**

```text
Let's stop here for today. Wrap up.
```

**What the agent does (`session-end`):**

1. Writes an ADR for each decision this session that has none yet.
2. Makes the final checkpoint. Its `Next:` must let a session that knows nothing of this
   conversation start immediately.
3. Runs the gate tests, asking first if slow tests would take long.
4. If model code changed, checks the implementation and verification links and the model
   overview in `docs/theory.md`, and reports remaining `[TBD]` items.
5. When every `gate:` is closed (or only `blocked:` ones remain), proposes merging into `main`.
6. When curation is due, suggests `/tune-docs` without running it.
7. Closes all todos and reports in three lines: what was done, `Next:`, and whether it merged.

**You approve:** the merge into `main`. The agent merges with `git merge --no-ff` and never
squashes, so checkpoint history is kept.

**The agent does not push.** If you use a remote, push yourself:

```powershell
git push
```

If any gate is still open, no merge is proposed; the next session continues on the same branch.

## 8. Scenario 6 — A criterion blocked by something external

Criteria waiting for measurements, equipment, or another team are marked `blocked:`:

```python
@pytest.mark.xfail(strict=True, reason="blocked: 77 K data from fab")
def test_77k():
    raise NotImplementedError
```

- `status` counts blocked gates separately: `Open gates for this leaf (2, 1 blocked)`.
- When only `blocked:` gates remain, the leaf may merge with your approval. The blocked gates stay
  visible as open on `main`.
- When the data arrives, open a new leaf that takes the gate over:

```text
The 77 K data arrived as data/run11_77K.csv. Let's pick up the blocked test_77k as a new leaf.
```

## 9. Scenario 7 — Periodic curation

**When:** when `session-end` suggests it (about 5 merged leaves, 3 or more `Learned:` lines, and
so on), or when the agent keeps forgetting the same thing.

**Preconditions:** a fresh session, on `main`, no uncommitted changes.

**Pass A — proposal:**

```text
/tune-docs
```

The agent runs the audit, harvests checkpoint lines, ADRs, and `.omo/` notepads, picks the facts
that deserve a permanent home, writes a proposal to `docs/_tuning-proposal.md`, and **stops**. It
changes no other file.

**Review:** answer by item ID.

```text
Approve A1, B1, B3, C1. Reject B2 — it came up only once. Hold D1.
```

**Pass B — apply (ideally in a fresh session):** on a `feature/curation-<date>` branch the agent
applies only the approved items, records the restructuring in an ADR, updates
`docs/.curation-state.json`, deletes the proposal, reruns the audit to verify, and proposes the
merge into `main`.

**You approve:** each proposal item, and the curation branch merge.

## 10. Scenario 8 — Coming back after days away; checking state yourself

You can check state from PowerShell without the agent:

```powershell
cd C:\projects\my-device-model

python tools\harness.py status                    # where things stand, next action, open gates
python tools\harness.py gates --all               # open gates across all leaves
python tools\harness.py harvest --keys Learned    # what has been learned so far
python tools\harness.py harvest --keys Tried      # approaches that failed
git log --oneline --first-parent main             # merged leaves
```

Then continue in opencode with `Run session-start.`

## 11. Scenario 9 — Adopting the harness in an existing project

- **If AGENTS.md exists**, `session-start` leaves its content alone and appends the harness
  section at the end. If it holds a lot of old `/init` output, the first curation will propose
  trimming it.
- **If there is no plan file**, plan with Prometheus first. `session-start` asks whether to plan
  first and stops when no plan exists.
- **Existing tests stay as they are.** Gates live only under `tests/gates/`.
- Commit or tidy any work in progress before starting; it keeps the first leaf clean.

## 12. What needs your approval

| The agent does on its own | Needs your approval | Never done |
|---|---|---|
| Create `feature/*` branches | `git init` | push |
| Checkpoint commits | The setup commit on `main` | rebase, reset, stash, amend |
| Write gate tests; remove markers when met | Merging into `main` | `git add -A`, `git add .` |
| Write ADRs | Applying curation proposal items | Deleting branches (only on request) |
| Update `docs/theory.md` | Merging the curation branch | opencode `/init` |
| Run `status`, `gates`, `harvest` | Running slow tests (asks first) | Writing a DOI from memory |
| | Handling a git-ignored plan file | Editing the installed skill files |

## 13. Updating the harness

When the harness repository changes, copy two things. Each project has its own copy of
`tools/harness.py`, so update it too:

```powershell
cd C:\projects\opencode-memory-harness
git pull

$proj = "C:\projects\my-device-model"
Copy-Item -Recurse -Force skills\* "$proj\.opencode\skills\"
Copy-Item -Force skills\session-start\scripts\harness.py "$proj\tools\harness.py"
```

The harness section in AGENTS.md is not updated automatically. If the new
`skills\session-start\templates\agents-section.md` differs, apply the change by hand or during
curation.

## 14. Troubleshooting

**The skills do not appear.**
Check the path is `<project>\.opencode\skills\<name>\SKILL.md` (plural `skills`), and that the
folder name matches `name:` at the top of SKILL.md. opencode searches from the working folder up
to the Git repository root. If they still do not appear, restart opencode.

**`/tune-docs` is missing.**
Check `<project>\.opencode\commands\tune-docs.md` (or `$HOME\.config\opencode\commands\`).
Without the command, "Run the context-curation skill" does the same.

**The agent runs long without checkpoints.**
Check that AGENTS.md contains the `<!-- memory-harness:start -->` section. If it does, remind the
agent: "Per AGENTS.md, rebuild the todo list as 5 items plus checkpoint, and make a checkpoint
now."

**The agent wants to commit on main.**
The checkpoint skill refuses to commit outside `feature/*` and tells you so. Decline and say:
"Open a leaf branch with session-start first."

**`status` looks odd.**

| Shown | Meaning and fix |
|---|---|
| `detached HEAD at ...` | On a commit, not a branch. `git switch <branch>` |
| `base 'main' not found` | The default branch is `master` or similar; the harness assumes `main`. Rename it (`git branch -m master main`) or run with `--base master` |
| `gate file ... is missing` | On a leaf branch with no gates. Have the agent write the gates first |
| `xfail is not strict` warning | A marker without `strict=True` would stay open after passing. Fix it |
| `no raises=...` warning | An import error could hide as "not yet met". Add `raises=` |

**A gate test shows FAILED instead of XFAIL.**
Usually an import error or a typo, surfaced by `raises=(AssertionError, NotImplementedError)`
instead of hidden; fix the test or the code. `XPASS(strict)` means the criterion is met while the
marker is still on; remove the marker.

**The audit reports `identifier without 'checked: ...'`.**
An identifier was written without a record of how it was checked. Provide the PDF or a DOI you
have verified. If it cannot be checked, `[TBD: source]` is the right entry.

**Commit messages break in PowerShell.**
PowerShell interprets `$` and backticks inside double quotes. Avoid them in commit messages, or
use single quotes.

**The agent suggests `/init`.**
Decline. AGENTS.md holds only the memory rules and routing. Facts that need a permanent home get
there through curation, with evidence.
