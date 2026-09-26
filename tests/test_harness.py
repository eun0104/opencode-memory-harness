"""Regression tests for skills/session-start/scripts/harness.py. Standard library only."""

import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "session-start" / "scripts"))

import harness  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}

GATES = textwrap.dedent('''
    import pytest
    import unittest
    from pytest import mark

    @pytest.mark.xfail(strict=True, raises=(AssertionError, NotImplementedError),
                       reason="gate: mobility within 5% at 300 K")
    def test_mobility_300k():
        assert False

    @mark.xfail(reason="gate: loose marker")
    def test_loose():
        assert False

    @pytest.mark.xfail(strict=True, reason="blocked: waiting for 77 K data")
    def test_77k():
        assert False

    def test_already_closed():
        assert True

    def helper_not_a_test():
        pass

    class TestContacts:
        @pytest.mark.xfail(strict=True, raises=AssertionError, reason="gate: Rc below 1 kOhm um")
        def test_rc(self):
            assert False

    class TestLegacy(unittest.TestCase):
        @unittest.expectedFailure
        def test_old(self):
            self.assertTrue(False)
''')


def sh(cwd, *args):
    env = dict(os.environ, **GIT_ENV)
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, env=env)


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = harness.main(argv)
    return code, buf.getvalue()


class Repo:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        sh(self.path, "init", "-q", "-b", "main")

    def write(self, rel, text):
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message, *paths):
        sh(self.path, "add", "--", *(paths or ["."]))
        sh(self.path, "commit", "-q", "-m", message)

    def sha(self):
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.path),
                              capture_output=True, text=True, check=True).stdout.strip()

    def close(self):
        self._tmp.cleanup()


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tests" / "gates").mkdir(parents=True)
        (self.root / "tests" / "gates" / "test_fit.py").write_text(GATES, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def gates(self):
        found, errors = harness.scan_gates(self.root)
        return {g["name"]: g for g in found}, errors

    def test_finds_only_marked_tests(self):
        gates, errors = self.gates()
        self.assertEqual(errors, [])
        self.assertEqual(set(gates), {"test_mobility_300k", "test_loose", "test_77k",
                                      "TestContacts.test_rc", "TestLegacy.test_old"})

    def test_reads_reason_strict_and_raises(self):
        gates, _ = self.gates()
        good = gates["test_mobility_300k"]
        self.assertEqual(good["reason"], "gate: mobility within 5% at 300 K")
        self.assertTrue(good["strict"])
        self.assertTrue(good["raises"])
        self.assertFalse(gates["test_loose"]["strict"])
        self.assertEqual(gates["TestLegacy.test_old"]["kind"], "expectedFailure")

    def test_warnings_flag_loose_markers_but_not_blocked(self):
        gates, _ = harness.scan_gates(self.root)
        text = "\n".join(harness.gate_warnings(gates))
        self.assertIn("test_loose: xfail is not strict", text)
        self.assertIn("test_loose: no raises", text)
        self.assertNotIn("test_77k", text)
        self.assertNotIn("test_mobility_300k", text)

    def test_ini_xfail_strict_makes_markers_strict(self):
        (self.root / "pytest.ini").write_text("[pytest]\nxfail_strict = true\n", encoding="utf-8")
        gates, _ = self.gates()
        self.assertTrue(gates["test_loose"]["strict"])

    def test_unparseable_file_is_reported_not_fatal(self):
        (self.root / "tests" / "test_broken.py").write_text("def x(:\n", encoding="utf-8")
        gates, errors = self.gates()
        self.assertIn("test_mobility_300k", gates)
        self.assertTrue(any("test_broken.py" in e for e in errors))

    def test_leaf_slug_to_gate_file(self):
        self.assertEqual(harness.leaf_slug("feature/fit-mobility"), "fit-mobility")
        self.assertIsNone(harness.leaf_slug("main"))
        self.assertEqual(harness.gate_file_for("fit-mobility").as_posix(),
                         "tests/gates/test_fit_mobility.py")


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.write("README.md", "demo\n")
        self.repo.commit("setup: harness", "README.md")
        self.repo.write("tests/gates/test_other.py",
                        "import pytest\n@pytest.mark.xfail(strict=True, raises=AssertionError,"
                        " reason='gate: other')\ndef test_other():\n    assert False\n")
        self.repo.commit("gates for other leaf", "tests/gates/test_other.py")

    def tearDown(self):
        self.repo.close()

    def status(self):
        return harness.build_status(self.repo.path, "main")

    def test_main_has_no_active_leaf(self):
        s = self.status()
        self.assertTrue(s["repo"])
        self.assertIsNone(s["leaf"])
        self.assertIsNone(s["next"])
        self.assertEqual(len(s["other_gates"]), 1)
        self.assertTrue(any("no active leaf" in n for n in s["notes"]))

    def test_feature_branch_reports_next_tried_and_leaf_gates(self):
        sh(self.repo.path, "switch", "-q", "-c", "feature/fit-mobility")
        self.repo.write("tests/gates/test_fit_mobility.py", GATES)
        self.repo.commit("checkpoint: gates written\n\nNext: implement mu(T)\n"
                         "Tried: power law — diverges below 100 K", "tests/gates/test_fit_mobility.py")
        self.repo.write("src/fit.py", "x = 1\n")
        self.repo.commit("checkpoint: fitter skeleton\n\nNext: run fit on run07.csv\n"
                         "Tried: scipy curve_fit default bounds — hits bound\n"
                         "Learned: [gotcha] run07.csv has a units row", "src/fit.py")
        self.repo.write("src/wip.py", "y = 2\n")

        s = self.status()
        self.assertEqual(s["leaf"], "fit-mobility")
        self.assertEqual(s["branch_commits"], 2)
        self.assertEqual(s["next"]["text"], "run fit on run07.csv")
        self.assertEqual(len(s["tried"]), 2)
        self.assertEqual(len(s["leaf_gates"]), 5)
        self.assertEqual([g["file"] for g in s["other_gates"]], ["tests/gates/test_other.py"])
        self.assertIn("src/wip.py", " ".join(s["uncommitted"]))

        text = harness.render_status(s)
        self.assertIn("Next: run fit on run07.csv", text)
        self.assertIn("Tried (do not repeat):", text)

    def test_feature_branch_without_gate_file_says_so(self):
        sh(self.repo.path, "switch", "-q", "-c", "feature/new-leaf")
        s = self.status()
        self.assertFalse(s["gate_file_exists"])
        self.assertTrue(any("write the gates first" in n for n in s["notes"]))
        self.assertTrue(any("no checkpoint with a Next" in n for n in s["notes"]))

    def test_trailers_from_main_do_not_leak_into_new_leaf(self):
        self.repo.write("a.txt", "a\n")
        self.repo.commit("checkpoint: old\n\nNext: stale action\nTried: stale attempt", "a.txt")
        sh(self.repo.path, "switch", "-q", "-c", "feature/fresh")
        s = self.status()
        self.assertIsNone(s["next"])
        self.assertEqual(s["tried"], [])

    def test_not_a_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = harness.build_status(Path(tmp), "main")
            self.assertFalse(s["repo"])
            self.assertIn("Repository:", harness.render_status(s))

    def test_cli_status_json(self):
        code, out = run(["--root", str(self.repo.path), "status", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["branch"], "main")

    def test_cli_defaults_to_status(self):
        code, out = run(["--root", str(self.repo.path)])
        self.assertEqual(code, 0)
        self.assertIn("Branch: main", out)


class HarvestTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.write("a.txt", "1\n")
        self.repo.commit("setup", "a.txt")
        self.since = self.repo.sha()
        sh(self.repo.path, "switch", "-q", "-c", "feature/leaf-one")
        self.repo.write("a.txt", "2\n")
        self.repo.commit("checkpoint: one\n\nNext: go on\nLearned: [gotcha] 한글 로그도 읽힌다\n"
                         "ADR: docs/adr/0002-model.md", "a.txt")
        sh(self.repo.path, "switch", "-q", "main")
        sh(self.repo.path, "merge", "-q", "--no-ff", "-m", "Merge feature/leaf-one",
           "feature/leaf-one")

    def tearDown(self):
        self.repo.close()

    def test_harvest_includes_merged_branch_trailers(self):
        code, out = run(["--root", str(self.repo.path), "harvest", "--since", self.since,
                         "--json"])
        self.assertEqual(code, 0)
        rows = json.loads(out)
        keys = sorted(r["key"] for r in rows)
        self.assertEqual(keys, ["ADR", "Learned"])
        self.assertIn("한글", [r for r in rows if r["key"] == "Learned"][0]["value"])

    def test_harvest_key_filter_and_unknown_key(self):
        _, out = run(["--root", str(self.repo.path), "harvest", "--keys", "Next", "--json"])
        self.assertEqual([r["value"] for r in json.loads(out)], ["go on"])
        code, _ = run(["--root", str(self.repo.path), "harvest", "--keys", "Bogus"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
