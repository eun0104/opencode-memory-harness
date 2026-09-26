#!/usr/bin/env python3
"""
docs_inventory.py - structural audit of a memory-harness project's persistent layer.

Standard library only. No network access. Never modifies the project.

Reports:
  1. Setup          - whether the harness section, plan path, and tools/harness.py exist
  2. Inventory      - persistent docs with layer, token count, and age
  3. Budget         - AGENTS.md against its L0 budget
  4. Reachability   - docs with no inbound pointer from AGENTS.md, and broken pointers
  5. Staleness      - docs untouched past the threshold (ADRs are exempt: they are records)
  6. Duplication    - near-identical paragraphs across different docs
  7. ADRs           - count, status, and records missing Status or Source
  8. Harvest        - merges and tagged checkpoint trailers since the last curation,
                      notepads under .omo/, and gate files that stayed open too long
  9. Theory         - docs/theory.md: every equation has source, implementation, and
                      verification that exist; every reference has a checked identifier

Usage:
    python docs_inventory.py --root .
    python docs_inventory.py --root . --json
    python docs_inventory.py --root . --stale-days 60 --l0-budget 1500
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

ENTRY_DOC = "AGENTS.md"
HARNESS_START = "<!-- memory-harness:start -->"
HARNESS_END = "<!-- memory-harness:end -->"
PLAN_LINE_RE = re.compile(r"^\s*-\s*Plan:\s*`([^`]+)`", re.MULTILINE)
TOOL_PATH = "tools/harness.py"
STATE_FILE = "docs/.curation-state.json"
ADR_DIR = "docs/adr"
GATES_DIR = "tests/gates"
NOTEPAD_GLOB = ".omo/**/notepads/**/*.md"
BASE_BRANCH = "main"

INCLUDE_GLOBS = ["*.md", "docs/**/*.md"]
EXCLUDE_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv", "archive",
                 ".opencode", ".omo"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKTICK_PATH_RE = re.compile(r"`([^`\s]+\.md)`")
BACKTICK_DIR_RE = re.compile(r"`([^`\s]+/)`")
VERIFIED_RE = re.compile(r"<!--\s*verified:\s*(\d{4}-\d{2}-\d{2})\s*-->", re.IGNORECASE)
ADR_STATUS_RE = re.compile(r"^\s*-\s*Status:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
ADR_SOURCE_RE = re.compile(r"^\s*-\s*Source:\s*\S", re.MULTILINE | re.IGNORECASE)
ADR_NAME_RE = re.compile(r"^(\d{4})-[\w.-]+\.md$")
TRAILER_RE = re.compile(r"^(Next|Tried|Evidence|Learned|ADR):\s*(.+?)\s*$")
TAG_RE = re.compile(r"^\[(\w+)\]")
XFAIL_TEXT_RE = re.compile(r"\bxfail\s*\(|\bexpectedFailure\b")

THEORY_DOC = "docs/theory.md"
EQ_HEADING_RE = re.compile(r"^###\s+(EQ-[\w.-]+)", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
FIELD_RE = r"^\s*-\s*{}:\s*(.*)$"
REF_CITE_RE = re.compile(r"\[(R\d+)\]")
REF_ENTRY_RE = re.compile(r"^-\s*\[(R\d+)\]", re.MULTILINE)
DOI_RE = re.compile(r"\bDOI:\s*(\S+)", re.IGNORECASE)
DOI_VALID_RE = re.compile(r"^10\.\d{4,9}/[^\s<>]+$")
OTHER_ID_RE = re.compile(r"\b(arXiv|ISBN|Internal):\s*\S+", re.IGNORECASE)
CHECKED_RE = re.compile(r"\bchecked:\s*(pdf|user|online)\b", re.IGNORECASE)
CODE_REF_RE = re.compile(r"`([^`\s]+\.py)::(\w+)`")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Rough token estimate for mixed ASCII / CJK text.

    ASCII prose runs about 4 characters per token; Korean and other CJK text
    is far denser, closer to 1.5 characters per token. This is an estimate,
    not a measurement - treat it as +/- 20%.
    """
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    wide_chars = len(text) - ascii_chars
    return int(ascii_chars / 4.0 + wide_chars / 1.5)


def rel_posix(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace(os.sep, "/")


def is_excluded(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in EXCLUDE_PARTS for part in rel_parts)


def collect(root: Path, globs):
    found = {}
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file() and not is_excluded(path, root):
                found[path.resolve()] = path
    return sorted(found.values(), key=lambda p: rel_posix(p, root))


def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def git(root: Path, *args: str):
    try:
        out = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=str(root),
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def git_last_commit(root: Path, rel: str):
    out = git(root, "log", "-1", "--format=%ad|%h", "--date=short", "--", rel)
    if out and out.strip():
        date, _, sha = out.strip().partition("|")
        return date, sha
    return None, None


def git_worktree_changed(root: Path, rel: str) -> bool:
    out = git(root, "status", "--porcelain", "--", rel)
    return bool(out and out.strip())


def freshness(text: str, mtime: float, commit_date=None):
    """Age in days since the latest committed state or valid verification marker."""
    latest = dt.date.fromtimestamp(mtime)
    if commit_date:
        try:
            latest = dt.date.fromisoformat(commit_date)
        except ValueError:
            pass
    verified = []
    for raw in VERIFIED_RE.findall(text):
        try:
            verified.append(dt.date.fromisoformat(raw))
        except ValueError:
            continue
    if verified:
        latest = max(latest, max(verified))
    return (max(0, (dt.date.today() - latest).days),
            max(verified).isoformat() if verified else None)


def harness_section(text: str):
    """Return the text between the harness markers, or None."""
    start, end = text.find(HARNESS_START), text.find(HARNESS_END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start:end]


def plan_path_from(agents_text: str):
    section = harness_section(agents_text) or ""
    match = PLAN_LINE_RE.search(section)
    return match.group(1).strip() if match else None


def classify_layer(rel: str, plan_rel) -> str:
    if rel == ENTRY_DOC:
        return "L0"
    if plan_rel and rel == plan_rel:
        return "L1"
    return "L2"


# --------------------------------------------------------------------------
# Pointers
# --------------------------------------------------------------------------

def strip_fenced_code(text: str) -> str:
    """Remove fenced examples so sample and placeholder paths are not pointers."""
    lines, in_code = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            lines.append(line)
    return "\n".join(lines)


def is_concrete(link: str) -> bool:
    return not any(ch in link for ch in "*?[]<>{}")


def extract_pointers(text: str):
    """(file links, directory links) outside fenced examples."""
    text = strip_fenced_code(text)
    files = set()
    for match in LINK_RE.findall(text):
        target = match.split("#")[0].strip()
        if target and not target.startswith(("http://", "https://", "mailto:")):
            files.add(target)
    files.update(BACKTICK_PATH_RE.findall(text))
    files = {f for f in files if f.endswith(".md") and is_concrete(f)}
    dirs = {d for d in BACKTICK_DIR_RE.findall(text) if is_concrete(d)}
    return files, dirs


def is_within(path: Path, directory: Path) -> bool:
    """Path.is_relative_to, which Python 3.8 lacks."""
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def resolve(link: str, source: Path, root: Path, want_dir: bool = False):
    candidates = ([(root / link.lstrip("/")).resolve()] if link.startswith("/")
                  else [(source.parent / link).resolve(), (root / link).resolve()])
    for candidate in candidates:
        if (candidate.is_dir() if want_dir else candidate.is_file()):
            return candidate
    return None


# --------------------------------------------------------------------------
# Duplication
# --------------------------------------------------------------------------

def paragraphs(text: str, min_words: int = 20):
    blocks, current, in_code = [], [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.strip():
            current.append(line.strip())
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return [b for b in blocks if len(b.split()) >= min_words]


def shingles(text: str, size: int = 5):
    words = re.findall(r"\w+", text.lower())
    if len(words) < size:
        return set()
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicates(docs_text, threshold: float):
    indexed = []
    for name, text in docs_text.items():
        for i, para in enumerate(paragraphs(text), start=1):
            sh = shingles(para)
            if sh:
                indexed.append((name, i, para, sh))
    hits = []
    for i in range(len(indexed)):
        for j in range(i + 1, len(indexed)):
            if indexed[i][0] == indexed[j][0]:
                continue
            score = jaccard(indexed[i][3], indexed[j][3])
            if score >= threshold:
                hits.append({"a": f"{indexed[i][0]} para {indexed[i][1]}",
                             "b": f"{indexed[j][0]} para {indexed[j][1]}",
                             "similarity": round(score, 2),
                             "excerpt": indexed[i][2][:110]})
    return sorted(hits, key=lambda h: -h["similarity"])


# --------------------------------------------------------------------------
# Harness-specific checks
# --------------------------------------------------------------------------

def read_state(root: Path):
    path = root / STATE_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"error": f"unreadable: {exc}"}


def audit_adrs(root: Path):
    adr_dir = root / ADR_DIR
    records, problems = [], []
    if not adr_dir.is_dir():
        return {"exists": False, "count": 0, "by_status": {}, "problems": []}
    numbers = {}
    for path in sorted(adr_dir.glob("*.md")):
        rel = rel_posix(path, root)
        match = ADR_NAME_RE.match(path.name)
        if not match:
            problems.append(f"{rel}: name is not NNNN-<slug>.md")
            continue
        numbers.setdefault(match.group(1), []).append(rel)
        text = read_text(path) or ""
        status = ADR_STATUS_RE.search(text)
        status_value = status.group(1).lower() if status else None
        if not status:
            problems.append(f"{rel}: no '- Status:' line")
        if not ADR_SOURCE_RE.search(text):
            problems.append(f"{rel}: no '- Source:' line")
        records.append({"path": rel, "status": status_value})
    for number, paths in numbers.items():
        if len(paths) > 1:
            problems.append(f"ADR number {number} used by {', '.join(paths)}")
    by_status = {}
    for record in records:
        key = (record["status"] or "missing").split()[0]
        by_status[key] = by_status.get(key, 0) + 1
    return {"exists": True, "count": len(records), "by_status": by_status, "problems": problems}


def harvest_summary(root: Path, since, base: str):
    """Merges into base and tagged trailers since the last curated commit."""
    summary = {"git": False, "base_exists": False, "since": since, "since_valid": None,
               "merges": 0, "trailers": {}, "learned_tags": {}}
    if git(root, "rev-parse", "--show-toplevel") is None:
        return summary
    summary["git"] = True
    if git(root, "rev-parse", "--verify", "--quiet", base) is None:
        return summary
    summary["base_exists"] = True
    rev_range = base
    if since:
        summary["since_valid"] = git(root, "rev-parse", "--verify", "--quiet",
                                     f"{since}^{{commit}}") is not None
        if summary["since_valid"]:
            rev_range = f"{since}..{base}"
    merges = git(root, "log", "--merges", "--first-parent", "--format=%h", rev_range) or ""
    summary["merges"] = len([line for line in merges.splitlines() if line.strip()])
    bodies = git(root, "log", "--format=%b%x1e", rev_range) or ""
    for body in bodies.split("\x1e"):
        for line in body.splitlines():
            match = TRAILER_RE.match(line.strip())
            if not match:
                continue
            key, value = match.groups()
            summary["trailers"][key] = summary["trailers"].get(key, 0) + 1
            if key == "Learned":
                tag = TAG_RE.match(value)
                name = tag.group(1) if tag else "untagged"
                summary["learned_tags"][name] = summary["learned_tags"].get(name, 0) + 1
    return summary


def sections(text: str):
    """{heading: body} for level-2 sections."""
    found = list(SECTION_RE.finditer(text))
    out = {}
    for i, match in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        out[match.group(1)] = text[match.end():end]
    return out


def field(block: str, name: str):
    """Value of a '- Name:' line, including indented continuation lines."""
    lines = block.splitlines()
    head = re.compile(FIELD_RE.format(re.escape(name)), re.IGNORECASE)
    for i, line in enumerate(lines):
        match = head.match(line)
        if not match:
            continue
        value = [match.group(1).strip()]
        for extra in lines[i + 1:]:
            if extra.startswith((" ", "\t")) and extra.strip() and not extra.lstrip().startswith("-"):
                value.append(extra.strip())
            else:
                break
        return " ".join(value)
    return None


def code_ref_problems(root: Path, eq: str, label: str, value: str):
    """Check `path.py::name` references: the file exists and defines the name."""
    problems = []
    for path, name in CODE_REF_RE.findall(value or ""):
        target = root / path
        if not target.is_file():
            problems.append(f"{eq}: {label} file `{path}` not found")
        elif not re.search(rf"^\s*(async\s+)?(def|class)\s+{re.escape(name)}\b",
                           read_text(target) or "", re.MULTILINE):
            problems.append(f"{eq}: {label} `{path}::{name}` not defined in that file")
    return problems


def audit_theory(root: Path):
    """Structure, citation, and code-link checks for docs/theory.md."""
    path = root / THEORY_DOC
    if not path.is_file():
        return {"exists": False}
    text = strip_fenced_code(read_text(path) or "")
    body = sections(text)
    problems, tbd = [], []

    heads = list(EQ_HEADING_RE.finditer(text))
    cited = set()
    for i, match in enumerate(heads):
        eq = match.group(1)
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        nxt = SECTION_RE.search(text, match.end())
        if nxt and nxt.start() < end:
            end = nxt.start()
        block = text[match.end():end]
        for name in ("Source", "Implementation", "Verification", "Status"):
            if field(block, name) is None:
                problems.append(f"{eq}: no '- {name}:' line")
        source = field(block, "Source") or ""
        refs = set(REF_CITE_RE.findall(source))
        cited |= refs
        if "[TBD" not in source and not refs and "derived here" not in source.lower():
            problems.append(f"{eq}: source cites no [Rn] reference, derivation, or [TBD: source]")
        for name in ("Symbols and units", "Assumptions", "Valid for", "Source",
                     "Implementation", "Verification"):
            if "[TBD" in (field(block, name) or ""):
                tbd.append(f"{eq}: {name.lower()}")
        for name in ("Implementation", "Verification"):
            problems += code_ref_problems(root, eq, name, field(block, name))

    references = body.get("References", "")
    entries = list(REF_ENTRY_RE.finditer(references))
    defined, dois = {}, {}
    for i, match in enumerate(entries):
        ref = match.group(1)
        end = entries[i + 1].start() if i + 1 < len(entries) else len(references)
        entry = references[match.start():end]
        defined[ref] = entry
        if "<" in entry and ">" in entry:
            problems.append(f"[{ref}]: template placeholder left in the entry")
        doi = DOI_RE.search(entry)
        has_other = OTHER_ID_RE.search(entry)
        if doi and doi.group(1).startswith("[TBD"):
            tbd.append(f"[{ref}]: identifier")
        elif doi:
            value = doi.group(1).rstrip(".,;")
            if not DOI_VALID_RE.match(value):
                problems.append(f"[{ref}]: malformed DOI `{value}`")
            dois.setdefault(value.lower(), []).append(ref)
        elif not has_other:
            if "[TBD" in entry:
                tbd.append(f"[{ref}]: identifier")
            else:
                problems.append(f"[{ref}]: no DOI, arXiv, ISBN, or Internal identifier, "
                                "and no [TBD: source]")
        if (doi and not doi.group(1).startswith("[TBD")) or has_other:
            if not CHECKED_RE.search(entry):
                problems.append(f"[{ref}]: identifier without 'checked: pdf | user | online'")
    for value, refs in dois.items():
        if len(refs) > 1:
            problems.append(f"DOI {value} appears in {', '.join('[' + r + ']' for r in refs)}")
    for ref in sorted(cited - set(defined)):
        problems.append(f"[{ref}] is cited but not listed under References")
    unused = sorted(set(defined) - cited - set(REF_CITE_RE.findall(
        "\n".join(v for k, v in body.items() if k not in ("References", "Equations")))))

    missing_sections = [name for name in ("Model overview", "Equations", "References")
                        if name not in body]
    return {"exists": True, "equations": len(heads), "references": len(defined),
            "problems": problems, "tbd": tbd, "unused_references": unused,
            "missing_sections": missing_sections}


def stale_gates(root: Path, stale_days: int):
    """Gate files that still contain xfail markers and were last committed long ago."""
    gates_dir = root / GATES_DIR
    found = []
    if not gates_dir.is_dir():
        return found
    for path in sorted(gates_dir.glob("*.py")):
        text = read_text(path) or ""
        open_count = len(XFAIL_TEXT_RE.findall(text))
        if not open_count:
            continue
        rel = rel_posix(path, root)
        date, _ = git_last_commit(root, rel)
        if not date:
            continue
        age = (dt.date.today() - dt.date.fromisoformat(date)).days
        if age > stale_days:
            found.append({"path": rel, "open_markers": open_count, "age_days": age})
    return found


# --------------------------------------------------------------------------
# Main audit
# --------------------------------------------------------------------------

def audit(root: Path, args) -> dict:
    agents_path = root / ENTRY_DOC
    agents_text = read_text(agents_path) if agents_path.is_file() else None
    section = harness_section(agents_text) if agents_text else None
    plan_rel = plan_path_from(agents_text) if agents_text else None
    plan_path = (root / plan_rel) if plan_rel else None

    setup = {
        "agents_md": agents_text is not None,
        "harness_section": section is not None,
        "plan_path": plan_rel,
        "plan_exists": bool(plan_path and plan_path.is_file()),
        "plan_ignored": bool(plan_rel and git(root, "check-ignore", "-q", plan_rel) is not None),
        "tool": (root / TOOL_PATH).is_file(),
    }
    if not setup["harness_section"]:
        mode = "not-set-up"
    elif not (setup["plan_exists"] and setup["tool"]):
        mode = "incomplete"
    else:
        mode = "ready"

    docs = collect(root, INCLUDE_GLOBS)
    texts, records = {}, []
    for path in docs:
        text = read_text(path)
        if text is None:
            continue
        rel = rel_posix(path, root)
        texts[rel] = text
        commit_date, sha = git_last_commit(root, rel)
        changed = bool(commit_date and git_worktree_changed(root, rel))
        age, verified = freshness(text, path.stat().st_mtime, None if changed else commit_date)
        records.append({"path": rel, "layer": classify_layer(rel, plan_rel),
                        "lines": text.count("\n") + 1, "tokens": estimate_tokens(text),
                        "age_days": age, "last_verified": verified, "git_date": commit_date,
                        "git_sha": sha, "worktree_changed": changed})

    plan_tokens = None
    if setup["plan_exists"]:
        plan_tokens = estimate_tokens(read_text(plan_path) or "")

    budget = None
    if agents_text is not None:
        tokens = estimate_tokens(agents_text)
        budget = {"tokens": tokens, "budget": args.l0_budget,
                  "over": max(0, tokens - args.l0_budget)}

    # -- reachability ----------------------------------------------------
    broken_candidates, edges = [], {}
    for rel, text in texts.items():
        source = root / rel
        files, dirs = extract_pointers(text)
        targets = set()
        for link in files:
            hit = resolve(link, source, root)
            if hit is None:
                broken_candidates.append({"from": rel, "link": link})
            else:
                try:
                    targets.add(rel_posix(hit, root))
                except ValueError:
                    pass
        for link in dirs:
            hit = resolve(link, source, root, want_dir=True)
            if hit is None:
                if link.startswith("docs/"):
                    broken_candidates.append({"from": rel, "link": link})
                continue
            for doc in texts:
                if is_within((root / doc).resolve(), hit):
                    targets.add(doc)
        edges[rel] = targets

    reached, queue = set(), [ENTRY_DOC] if ENTRY_DOC in texts else []
    while queue:
        node = queue.pop()
        if node in reached:
            continue
        reached.add(node)
        queue.extend(edges.get(node, ()))
    if agents_text is None:
        broken, orphans = [], []
    else:
        broken = [b for b in broken_candidates if b["from"] in reached]
        orphans = sorted(rel for rel in texts if rel not in reached and rel != ENTRY_DOC)

    # -- staleness (ADRs are immutable records, so they are exempt) ------
    stale = sorted(({"path": r["path"], "age_days": r["age_days"],
                     "last_verified": r["last_verified"]}
                    for r in records
                    if r["age_days"] > args.stale_days
                    and not r["path"].startswith(ADR_DIR + "/")),
                   key=lambda s: -s["age_days"])

    state = read_state(root)
    since = (state or {}).get("last_curated_commit") if state and not state.get("error") else None
    notepads = [p for p in root.glob(NOTEPAD_GLOB) if p.is_file()]

    return {
        "root": str(root),
        "mode": mode,
        "setup": setup,
        "docs": records,
        "plan_tokens": plan_tokens,
        "budget": budget,
        "broken_links": broken,
        "orphans": orphans,
        "stale": stale,
        "duplicates": find_duplicates(texts, args.dup_threshold),
        "adrs": audit_adrs(root),
        "harvest": harvest_summary(root, since, args.base),
        "notepads": {"files": len(notepads),
                     "tokens": sum(estimate_tokens(read_text(p) or "") for p in notepads)},
        "stale_gates": stale_gates(root, args.stale_days),
        "theory": audit_theory(root),
        "curation_state": state,
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def report(result: dict, args) -> str:
    out = ["# Documentation Inventory", ""]
    setup = result["setup"]
    mode = result["mode"]
    if mode == "not-set-up":
        out += ["Mode: **not set up** — AGENTS.md has no memory-harness section. Run "
                "`session-start` first; curation needs a harness project.", ""]
    elif mode == "incomplete":
        missing = []
        if not setup["plan_path"]:
            missing.append("no `- Plan:` line in the harness section")
        elif not setup["plan_exists"]:
            missing.append(f"plan file `{setup['plan_path']}` not found")
        if not setup["tool"]:
            missing.append(f"`{TOOL_PATH}` missing")
        out += ["Mode: **incomplete** — " + "; ".join(missing) + ".", ""]
    else:
        out += ["Mode: **ready**", ""]
    if setup["plan_ignored"]:
        out += [f"Note: plan `{setup['plan_path']}` is git-ignored, so it is not versioned.", ""]

    state = result["curation_state"]
    if state and state.get("error"):
        out.append(f"Curation state: **{state['error']}**")
    elif state and state.get("last_curated"):
        out.append(f"Last curated: **{state['last_curated']}** at commit "
                   f"`{state.get('last_curated_commit') or '?'}`")
    else:
        out.append("Last curated: **never**")
    out.append("")

    out += ["## 1. Inventory", "",
            "| Doc | Layer | Lines | ~Tokens | Age (d) | Last commit |",
            "|---|---|---:|---:|---:|---|"]
    for r in sorted(result["docs"], key=lambda x: (x["layer"], x["path"])):
        commit = f"{r['git_date']} {r['git_sha']}" if r["git_date"] else "-"
        if r["worktree_changed"]:
            commit += " (working tree changed)"
        out.append(f"| `{r['path']}` | {r['layer']} | {r['lines']} | {r['tokens']} | "
                   f"{r['age_days']} | {commit} |")
    if result["plan_tokens"] is not None:
        out += ["", f"Plan (L1, planner-owned, not budgeted): `{setup['plan_path']}`, "
                    f"~{result['plan_tokens']} tokens."]
    out.append("")

    out += ["## 2. Budget", ""]
    b = result["budget"]
    if b is None:
        out.append(f"- `{ENTRY_DOC}` **NOT FOUND**.")
    elif b["over"]:
        out.append(f"- `{ENTRY_DOC}`: {b['tokens']} tokens (budget {b['budget']}) - "
                   f"**OVER by {b['over']}**. See `references/audit-checks.md` section 1.")
    else:
        out.append(f"- `{ENTRY_DOC}`: {b['tokens']} / {b['budget']} tokens - ok")
    out.append("")

    out += ["## 3. Reachability", ""]
    if result["broken_links"]:
        out.append("**Broken pointers (fix first):**")
        out.extend(f"- `{x['from']}` -> `{x['link']}` (target missing)"
                   for x in result["broken_links"])
    else:
        out.append("No broken pointers.")
    out.append("")
    if result["orphans"]:
        out.append("**Unreachable from AGENTS.md:**")
        out.extend(f"- `{o}`" for o in result["orphans"])
    else:
        out.append("No orphan docs.")
    out.append("")

    out += ["## 4. Staleness", ""]
    if result["stale"]:
        for s in result["stale"]:
            basis = f", last verified {s['last_verified']}" if s["last_verified"] else ""
            out.append(f"- `{s['path']}` - {s['age_days']} days{basis} "
                       f"(threshold {args.stale_days})")
        out += ["", "Verify against the code or data, then add or replace "
                    "`<!-- verified: YYYY-MM-DD -->`."]
    else:
        out.append("Nothing stale. (ADRs are exempt; they are records.)")
    out.append("")

    out += ["## 5. Duplication", ""]
    if result["duplicates"]:
        for d in result["duplicates"][:15]:
            out.append(f"- {d['a']} ~ {d['b']} (similarity {d['similarity']})")
            out.append(f"  > {d['excerpt']}...")
    else:
        out.append("No near-duplicate passages above threshold.")
    out.append("")

    adrs = result["adrs"]
    out += ["## 6. ADRs", ""]
    if not adrs["exists"]:
        out.append(f"`{ADR_DIR}/` does not exist.")
    else:
        statuses = ", ".join(f"{k}: {v}" for k, v in sorted(adrs["by_status"].items())) or "none"
        out.append(f"{adrs['count']} ADR(s) — {statuses}.")
        out.extend(f"- {p}" for p in adrs["problems"])
    out.append("")

    h = result["harvest"]
    out += ["## 7. Harvest sources", ""]
    if not h["git"]:
        out.append("Not a Git work tree: no checkpoint history to harvest.")
    elif not h["base_exists"]:
        out.append(f"Base branch `{args.base}` not found.")
    else:
        scope = (f"since `{h['since']}`" if h["since"] and h["since_valid"]
                 else "over the whole history")
        if h["since"] and h["since_valid"] is False:
            out.append(f"Warning: last curated commit `{h['since']}` not found; "
                       "counting the whole history.")
        out.append(f"{h['merges']} merged leaf branch(es) into `{args.base}` {scope}.")
        trailers = ", ".join(f"{k}: {v}" for k, v in sorted(h["trailers"].items())) or "none"
        out.append(f"Checkpoint trailers: {trailers}.")
        if h["learned_tags"]:
            tags = ", ".join(f"[{k}] {v}" for k, v in sorted(h["learned_tags"].items()))
            out.append(f"Learned tags: {tags}.")
        since_arg = f" --since {h['since']}" if h["since"] and h["since_valid"] else ""
        out.append(f"Read them with `python tools/harness.py harvest{since_arg}`.")
    n = result["notepads"]
    if n["files"]:
        out.append(f"Notepads under `.omo/`: {n['files']} file(s), ~{n['tokens']} tokens.")
    if result["stale_gates"]:
        out += ["", "**Gate files open too long:**"]
        out.extend(f"- `{g['path']}` - {g['open_markers']} open marker(s), last commit "
                   f"{g['age_days']} days ago" for g in result["stale_gates"])
    out.append("")

    t = result["theory"]
    if t["exists"]:
        out += ["## 8. Theory document", "",
                f"`{THEORY_DOC}`: {t['equations']} equation(s), {t['references']} reference(s)."]
        if t["missing_sections"]:
            out.append("Missing sections: " + ", ".join(t["missing_sections"]) + ".")
        if t["problems"]:
            out += ["", "**Problems (fix before trusting the document):**"]
            out.extend(f"- {p}" for p in t["problems"])
        if t["tbd"]:
            out += ["", "Open `[TBD]` links: " + "; ".join(t["tbd"]) + "."]
        if t["unused_references"]:
            out.append("Listed but never cited: "
                       + ", ".join(f"[{r}]" for r in t["unused_references"]) + ".")
        if not (t["problems"] or t["tbd"] or t["missing_sections"]):
            out.append("Every equation has a source, implementation, and verification; every "
                       "reference has a checked identifier.")
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--json", action="store_true", help="emit raw JSON")
    parser.add_argument("--base", default=BASE_BRANCH, help="integration branch (default: main)")
    parser.add_argument("--l0-budget", type=int, default=2000,
                        help="token budget for AGENTS.md (default: 2000)")
    parser.add_argument("--stale-days", type=int, default=90,
                        help="flag docs and open gate files older than this (default: 90)")
    parser.add_argument("--dup-threshold", type=float, default=0.45,
                        help="paragraph similarity to flag, 0-1 (default: 0.45)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1
    result = audit(root, args)
    text = json.dumps(result, indent=2, ensure_ascii=False) if args.json else report(result, args)
    try:
        print(text)
    except BrokenPipeError:
        os.close(sys.stdout.fileno())
    return 0 if result["mode"] == "ready" else 2


if __name__ == "__main__":
    sys.exit(main())
