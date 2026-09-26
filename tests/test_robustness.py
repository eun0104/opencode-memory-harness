"""Robustness tests: conditions met on real Windows machines and real repositories.

Each test pins a failure found while probing the harness outside the happy path.
Standard library only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "session-start" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "context-curation" / "scripts"))

import docs_inventory as inv  # noqa: E402
import harness  # noqa: E402
from test_docs_inventory import GOOD_THEORY, Project, args  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@example.invalid",
           "GIT_CONFIG_NOSYSTEM": "1"}
GATE = ("import pytest\n@pytest.mark.xfail(strict=True, raises=AssertionError, "
        "reason='gate: x')\ndef test_x():\n    assert False\n")


def git(cwd, *argv):
    subprocess.run(["git", *argv], cwd=str(cwd), check=True, capture_output=True,
                   env=dict(os.environ, **GIT_ENV))


class Repo:
    def __init__(self, branch="main"):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        git(self.path, "init", "-q", "-b", branch)

    def write(self, rel, text, newline=None):
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(text)

    def commit(self, *messages, paths=("--", ".")):
        git(self.path, "add", *paths)
        argv = ["commit", "-q"]
        for message in messages:
            argv += ["-m", message]
        git(self.path, *argv)

    def status(self):
        return harness.build_status(self.path, "main")

    def close(self):
        self._tmp.cleanup()


class BranchStateTests(unittest.TestCase):
    def test_repository_without_commits(self):
        repo = Repo()
        try:
            s = repo.status()
            self.assertEqual(s["branch"], "main")
            self.assertIn("no commits yet on 'main'", s["notes"])
            self.assertIn("Branch: main", harness.render_status(s))
        finally:
            repo.close()

    def test_detached_head_is_named_as_such(self):
        repo = Repo()
        try:
            repo.write("a.txt", "a\n")
            repo.commit("init")
            git(repo.path, "checkout", "-q", "--detach")
            s = repo.status()
            self.assertIsNone(s["branch"])
            self.assertIsNotNone(s["detached"])
            self.assertIn("(detached HEAD at", harness.render_status(s))
        finally:
            repo.close()

    def test_missing_base_is_not_reported_as_since_main(self):
        repo = Repo(branch="master")
        try:
            repo.write("a.txt", "a\n")
            repo.commit("init")
            git(repo.path, "switch", "-q", "-c", "feature/x")
            text = harness.render_status(repo.status())
            self.assertIn("in total; base 'main' not found", text)
            self.assertNotIn("since main", text)
        finally:
            repo.close()


class PathTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.write("a.txt", "a\n")
        self.repo.commit("init")

    def tearDown(self):
        self.repo.close()

    def test_paths_with_spaces_and_korean_are_unquoted(self):
        self.repo.write("space name.py", "x\n")
        self.repo.write("모델 파일.py", "y\n")
        uncommitted = self.repo.status()["uncommitted"]
        self.assertIn("space name.py", uncommitted)
        self.assertIn("모델 파일.py", uncommitted)
        self.assertFalse(any('"' in p for p in uncommitted))

    def test_rename_reports_the_new_path_once(self):
        git(self.repo.path, "mv", "a.txt", "b.txt")
        self.assertEqual(self.repo.status()["uncommitted"], ["b.txt"])

    def test_korean_leaf_slug_keeps_its_letters(self):
        self.assertEqual(harness.gate_file_for("한글-leaf").as_posix(),
                         "tests/gates/test_한글_leaf.py")
        git(self.repo.path, "switch", "-q", "-c", "feature/한글-leaf")
        self.repo.write("tests/gates/test_한글_leaf.py", GATE)
        self.assertEqual(len(self.repo.status()["leaf_gates"]), 1)

    def test_korean_trailers_round_trip(self):
        git(self.repo.path, "switch", "-q", "-c", "feature/fit")
        self.repo.write("b.txt", "b\n")
        self.repo.commit("checkpoint: 한글", "Next: 이동도 피팅 다시 실행", "Tried: 방법 A — 발산")
        s = self.repo.status()
        self.assertEqual(s["next"]["text"], "이동도 피팅 다시 실행")
        self.assertEqual(s["tried"], ["방법 A — 발산"])


class WindowsFileTests(unittest.TestCase):
    """CRLF line endings and the UTF-8 BOM that Windows editors write."""

    def test_gate_file_with_bom_and_crlf_is_scanned(self):
        repo = Repo()
        try:
            repo.write("tests/gates/test_x.py", "﻿" + GATE, newline="\r\n")
            gates, errors = harness.scan_gates(repo.path)
            self.assertEqual(errors, [])
            self.assertEqual([g["name"] for g in gates], ["test_x"])
        finally:
            repo.close()

    def test_crlf_trailers_are_parsed(self):
        self.assertEqual(harness.parse_trailers("Next: go\r\nTried: a — b\r\n"),
                         [("Next", "go"), ("Tried", "a — b")])

    def test_inventory_with_crlf_bom_and_korean(self):
        p = Project()
        try:
            p.harness(plan=".omo/plans/이동도 계획.md")
            agents = (p.root / "AGENTS.md").read_text(encoding="utf-8")
            with open(p.root / "AGENTS.md", "w", encoding="utf-8-sig", newline="\r\n") as h:
                h.write(agents + "| `docs/theory.md` | 물리 모델을 바꿀 때 |\n")
            with open(p.root / "docs/theory.md", "w", encoding="utf-8-sig", newline="\r\n") as h:
                h.write(GOOD_THEORY.replace("Field-dependent mobility", "전계 의존 이동도"))
            p.write("src/mobility.py", "﻿def mu(E, mu0, Ec):\n    return 0\n")
            p.write("tests/gates/test_fit.py", "def test_low_field_limit():\n    pass\n")
            result = p.audit()
            self.assertEqual(result["mode"], "ready")
            self.assertEqual(result["setup"]["plan_path"], ".omo/plans/이동도 계획.md")
            self.assertEqual(result["broken_links"], [])
            self.assertEqual(result["theory"]["problems"], [])
        finally:
            p.close()

    def test_state_file_with_bom_is_read(self):
        p = Project()
        try:
            p.harness()
            with open(p.root / "docs/.curation-state.json", "w", encoding="utf-8-sig") as h:
                json.dump({"last_curated": "2026-09-01", "last_curated_commit": None}, h)
            state = p.audit()["curation_state"]
            self.assertEqual(state.get("last_curated"), "2026-09-01")
        finally:
            p.close()


class ScaleTests(unittest.TestCase):
    def test_status_scans_many_gate_files_quickly(self):
        import time
        repo = Repo()
        try:
            for i in range(300):
                repo.write(f"tests/gates/test_{i}.py", GATE)
            start = time.perf_counter()
            s = repo.status()
            self.assertEqual(len(s["other_gates"]), 300)
            self.assertLess(time.perf_counter() - start, 5.0)
        finally:
            repo.close()


if __name__ == "__main__":
    unittest.main()
