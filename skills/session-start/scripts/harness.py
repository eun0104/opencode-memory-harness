#!/usr/bin/env python3
"""harness.py - where does the work stand? Read from Git and the gate tests, not from notes.

Standard library only. No network. Never modifies the repository.

Commands:
    python tools/harness.py status            # run first after compaction or at session start
    python tools/harness.py gates [--all]     # open gates (xfail tests), found without running tests
    python tools/harness.py harvest [--since REF] [--keys Learned,Tried]
                                              # checkpoint trailers, for context-curation

Conventions (docs/DESIGN.md):
    - one plan leaf = branch feature/<leaf>; its gates live in tests/gates/test_<leaf>.py
    - an open gate is a test marked @pytest.mark.xfail(strict=True, raises=..., reason="gate: ...")
    - checkpoint commits carry trailers: Next, Tried, Evidence, Learned, ADR
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

TRAILER_KEYS = ("Next", "Tried", "Evidence", "Learned", "ADR")
TRAILER_RE = re.compile(r"^(%s):\s*(.+?)\s*$" % "|".join(TRAILER_KEYS))
FEATURE_PREFIX = "feature/"
GATES_DIR = Path("tests") / "gates"
TEST_ROOTS = ("tests",)
INI_FILES = ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini")
XFAIL_STRICT_INI_RE = re.compile(r"^\s*xfail_strict\s*=\s*(true|1|yes)\s*$",
                                 re.IGNORECASE | re.MULTILINE)
RECORD_SEP, FIELD_SEP = "\x1e", "\x1f"


# --------------------------------------------------------------------------
# Git
# --------------------------------------------------------------------------

def git(root: Path, *args: str):
    """Run git; return stdout, or None when git is missing or the command fails."""
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args], cwd=str(root),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def parse_trailers(body: str):
    found = []
    for line in body.splitlines():
        match = TRAILER_RE.match(line.strip())
        if match:
            found.append((match.group(1), match.group(2)))
    return found


def commits(root: Path, rev_range: str, limit: int = 0):
    """Commits in rev_range, newest first, with parsed trailers."""
    args = ["log", "--date=short", f"--format=%H{FIELD_SEP}%ad{FIELD_SEP}%s{FIELD_SEP}%b{RECORD_SEP}"]
    if limit:
        args.append(f"-n{limit}")
    args.append(rev_range)
    out = git(root, *args)
    if not out:
        return []
    result = []
    for record in out.split(RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(FIELD_SEP)
        if len(parts) < 4:
            continue
        sha, date, subject, body = parts[0], parts[1], parts[2], parts[3]
        result.append({"sha": sha[:10], "date": date, "subject": subject,
                       "trailers": parse_trailers(body)})
    return result


def leaf_slug(branch):
    if not branch or not branch.startswith(FEATURE_PREFIX):
        return None
    return branch[len(FEATURE_PREFIX):]


CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints"}


def is_cache_path(path: str) -> bool:
    """Tool caches are never work in flight; hiding them keeps status from inviting a bad commit."""
    return any(part in CACHE_PARTS for part in path.strip('"').replace("\\", "/").split("/"))


def is_blocked(gate) -> bool:
    return gate["reason"].startswith("blocked:")


def gate_file_for(slug: str) -> Path:
    return GATES_DIR / ("test_" + re.sub(r"[^0-9A-Za-z_]", "_", slug) + ".py")


# --------------------------------------------------------------------------
# Static gate scan
# --------------------------------------------------------------------------

def dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def ini_strict(root: Path) -> bool:
    for name in INI_FILES:
        path = root / name
        try:
            if path.is_file() and XFAIL_STRICT_INI_RE.search(path.read_text(encoding="utf-8")):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def xfail_info(decorator, default_strict: bool):
    call = decorator if isinstance(decorator, ast.Call) else None
    name = dotted(call.func if call else decorator)
    last = name.rsplit(".", 1)[-1]
    if last == "expectedFailure":
        return {"kind": "expectedFailure", "reason": "", "strict": True, "raises": False,
                "conditional": False, "opaque": False}
    if last != "xfail":
        return None
    info = {"kind": "xfail", "reason": "", "strict": default_strict, "raises": False,
            "conditional": bool(call and call.args), "opaque": False}
    for kw in (call.keywords if call else []):
        if kw.arg is None:
            info["opaque"] = True  # **options: strict/raises cannot be read statically
        elif kw.arg == "reason" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            info["reason"] = kw.value.value
        elif kw.arg == "strict" and isinstance(kw.value, ast.Constant):
            info["strict"] = bool(kw.value.value)
        elif kw.arg == "raises":
            info["raises"] = True
    return info


class GateVisitor(ast.NodeVisitor):
    def __init__(self, rel: str, default_strict: bool):
        self.rel, self.default_strict = rel, default_strict
        self.stack, self.gates = [], []

    def _check(self, node, is_test: bool):
        for decorator in node.decorator_list:
            info = xfail_info(decorator, self.default_strict)
            if info and is_test:
                info.update(file=self.rel, line=node.lineno,
                            name=".".join(self.stack + [node.name]))
                self.gates.append(info)

    def visit_FunctionDef(self, node):
        self._check(node, node.name.startswith("test"))

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._check(node, node.name.startswith("Test"))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()


def scan_gates(root: Path):
    """Find xfail/expectedFailure tests without running them. Returns (gates, errors)."""
    default_strict = ini_strict(root)
    gates, errors = [], []
    for top in TEST_ROOTS:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                errors.append(f"{rel}: cannot parse ({exc.__class__.__name__})")
                continue
            visitor = GateVisitor(rel, default_strict)
            visitor.visit(tree)
            gates.extend(visitor.gates)
    return gates, errors


def gate_warnings(gates):
    warnings = []
    for gate in gates:
        if gate["kind"] != "xfail" or gate["opaque"]:
            continue
        where = f"{gate['file']}:{gate['line']} {gate['name']}"
        if not gate["strict"]:
            warnings.append(f"{where}: xfail is not strict; a met gate would stay marked open")
        if not gate["raises"] and not gate["reason"].startswith("blocked:"):
            warnings.append(f"{where}: no raises=...; an import error would count as 'not yet met'")
    return warnings


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def build_status(root: Path, base: str) -> dict:
    status = {"git": True, "repo": False, "branch": None, "base": base, "leaf": None,
              "gate_file": None, "gate_file_exists": False, "next": None, "tried": [],
              "evidence": [], "branch_commits": 0, "leaf_gates": [], "other_gates": [],
              "uncommitted": [], "hidden_cache_paths": 0, "warnings": [], "notes": []}
    if git(root, "--version") is None:
        status["git"] = False
        status["notes"].append("git is not available")
    elif git(root, "rev-parse", "--show-toplevel") is None:
        status["notes"].append("not a Git work tree")
    else:
        status["repo"] = True
        branch = (git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
        status["branch"] = branch or None
        slug = leaf_slug(branch)
        base_exists = git(root, "rev-parse", "--verify", "--quiet", base) is not None
        if slug:
            status["leaf"] = slug
            rev_range = f"{base}..HEAD" if base_exists else "HEAD"
            if not base_exists:
                status["notes"].append(f"base branch '{base}' not found; showing all history")
            history = commits(root, rev_range)
            status["branch_commits"] = len(history)
            for commit in history:
                for key, value in commit["trailers"]:
                    if key == "Next" and status["next"] is None:
                        status["next"] = {"text": value, "sha": commit["sha"],
                                          "subject": commit["subject"]}
                    elif key == "Tried":
                        status["tried"].append(value)
                    elif key == "Evidence":
                        status["evidence"].append(value)
            if status["next"] is None:
                status["notes"].append("no checkpoint with a Next: trailer on this branch yet")
        elif branch:
            status["notes"].append(f"on '{branch}', not a feature/* branch: no active leaf")
        porcelain = git(root, "status", "--porcelain") or ""
        paths = [line[3:] for line in porcelain.splitlines() if line.strip()]
        status["uncommitted"] = [p for p in paths if not is_cache_path(p)]
        status["hidden_cache_paths"] = len(paths) - len(status["uncommitted"])

    gates, errors = scan_gates(root)
    status["warnings"].extend(errors)
    status["warnings"].extend(gate_warnings(gates))
    if status["leaf"]:
        gate_file = gate_file_for(status["leaf"]).as_posix()
        status["gate_file"] = gate_file
        status["gate_file_exists"] = (root / gate_file).is_file()
        if not status["gate_file_exists"]:
            status["notes"].append(f"gate file {gate_file} is missing: write the gates first")
        status["leaf_gates"] = [g for g in gates if g["file"] == gate_file]
        status["other_gates"] = [g for g in gates if g["file"] != gate_file]
    else:
        status["other_gates"] = gates
    return status


def gate_line(gate) -> str:
    reason = gate["reason"] or "(no reason)"
    return f"  - {gate['file']}:{gate['line']} {gate['name']} — {reason}"


def render_status(s: dict) -> str:
    out = []
    if not s["repo"]:
        out.append("Repository: " + "; ".join(s["notes"]))
    else:
        out.append(f"Branch: {s['branch']}" + (f"  (leaf: {s['leaf']}, "
                   f"{s['branch_commits']} commit(s) since {s['base']})" if s["leaf"] else ""))
        if s["next"]:
            out.append(f"Next: {s['next']['text']}")
            out.append(f"  from {s['next']['sha']} \"{s['next']['subject']}\"")
        if s["tried"]:
            out.append("Tried (do not repeat):")
            out.extend(f"  - {item}" for item in s["tried"])
    if s["leaf"]:
        blocked = [g for g in s["leaf_gates"] if is_blocked(g)]
        detail = f", {len(blocked)} blocked" if blocked else ""
        out.append(f"Open gates for this leaf ({len(s['leaf_gates'])}{detail}) in {s['gate_file']}:")
        if s["leaf_gates"]:
            out.extend(gate_line(g) for g in s["leaf_gates"])
            if len(blocked) == len(s["leaf_gates"]):
                out.append("  only blocked gates remain: the leaf may merge with the user's "
                           "approval; the blocked gates stay open on main")
        elif s["gate_file_exists"]:
            out.append("  none - run the gate tests; if they pass, the leaf is ready to merge")
        else:
            out.append("  none")
    if s["other_gates"]:
        files = sorted({g["file"] for g in s["other_gates"]})
        blocked = sum(1 for g in s["other_gates"] if is_blocked(g))
        label = "Open gates" if not s["leaf"] else "Open gates elsewhere"
        detail = f" ({blocked} blocked)" if blocked else ""
        out.append(f"{label}: {len(s['other_gates'])}{detail} in {len(files)} file(s): "
                   f"{', '.join(files)}")
    if s["repo"]:
        hidden = s.get("hidden_cache_paths", 0)
        out.append("Uncommitted: " + (", ".join(s["uncommitted"]) if s["uncommitted"] else "none")
                   + (f"  ({hidden} tool-cache path(s) hidden)" if hidden else ""))
    notes = s["notes"] if s["repo"] else []
    for note in notes:
        out.append(f"Note: {note}")
    for warning in s["warnings"]:
        out.append(f"Warning: {warning}")
    return "\n".join(out)


def cmd_status(args) -> int:
    status = build_status(Path(args.root).resolve(), args.base)
    print(json.dumps(status, ensure_ascii=False, indent=2) if args.json else render_status(status))
    return 0


def cmd_gates(args) -> int:
    root = Path(args.root).resolve()
    gates, errors = scan_gates(root)
    if not args.all:
        branch = (git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
        slug = leaf_slug(branch)
        if slug:
            target = gate_file_for(slug).as_posix()
            gates = [g for g in gates if g["file"] == target]
    if args.json:
        print(json.dumps({"gates": gates, "errors": errors}, ensure_ascii=False, indent=2))
    else:
        print(f"Open gates: {len(gates)}")
        for gate in gates:
            print(gate_line(gate))
        for line in errors + gate_warnings(gates):
            print(f"Warning: {line}")
    return 0


def cmd_harvest(args) -> int:
    root = Path(args.root).resolve()
    keys = {k.strip() for k in args.keys.split(",") if k.strip()}
    unknown = keys - set(TRAILER_KEYS)
    if unknown:
        print(f"Unknown trailer key(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    if git(root, "rev-parse", "--show-toplevel") is None:
        print("Not a Git work tree.", file=sys.stderr)
        return 1
    rev_range = f"{args.since}..HEAD" if args.since else "HEAD"
    rows = []
    for commit in commits(root, rev_range):
        for key, value in commit["trailers"]:
            if key in keys:
                rows.append({"sha": commit["sha"], "date": commit["date"], "key": key,
                             "value": value})
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"{len(rows)} trailer line(s) in {rev_range}")
        for row in rows:
            print(f"{row['sha']} {row['date']} {row['key']}: {row['value']}")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="project root (default: .)")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="branch, next action, open gates, uncommitted")
    p_status.add_argument("--base", default="main")
    p_status.add_argument("--json", action="store_true")

    p_gates = sub.add_parser("gates", help="open gates found statically")
    p_gates.add_argument("--all", action="store_true", help="all gate files, not just this leaf")
    p_gates.add_argument("--json", action="store_true")

    p_harvest = sub.add_parser("harvest", help="checkpoint trailers for curation")
    p_harvest.add_argument("--since", help="commit to start after (exclusive)")
    p_harvest.add_argument("--keys", default="Learned,Tried,ADR,Evidence")
    p_harvest.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["--root", args.root, "status"])
    return {"status": cmd_status, "gates": cmd_gates, "harvest": cmd_harvest}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
