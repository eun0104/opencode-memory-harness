"""Regression tests for skills/context-curation/scripts/docs_inventory.py (v3.1 layout).

Standard library only. Projects are synthesized in temporary directories.
"""

import argparse
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "context-curation" / "scripts"))

import docs_inventory as inv  # noqa: E402

SECTION_TEMPLATE = ROOT / "skills" / "session-start" / "templates" / "agents-section.md"
ADR_TEMPLATE = ROOT / "skills" / "session-start" / "templates" / "adr-0001.md"
GIT_ENV = {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
           "GIT_CONFIG_NOSYSTEM": "1"}
PLAN = ".omo/plans/demo.md"


def args(**overrides):
    base = dict(l0_budget=2000, stale_days=90, dup_threshold=0.45, base="main")
    base.update(overrides)
    return argparse.Namespace(**base)


class Project:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def harness(self, plan=PLAN, extra=""):
        section = SECTION_TEMPLATE.read_text(encoding="utf-8").replace("<plan-path>", plan)
        self.write("AGENTS.md", "# Demo\n\n" + section + extra)
        self.write(plan, "# Plan\n- [ ] leaf one\n")
        self.write("tools/harness.py", "# stub\n")
        self.write("docs/adr/0001-record-decisions-as-adrs.md",
                   ADR_TEMPLATE.read_text(encoding="utf-8"))

    def git(self, *argv, env=None):
        full_env = dict(os.environ, **GIT_ENV, **(env or {}))
        return subprocess.run(["git", *argv], cwd=str(self.root), check=True,
                              capture_output=True, text=True, env=full_env).stdout

    def commit(self, message, *paths, env=None):
        self.git("add", "--", *(paths or ["."]), env=env)
        self.git("commit", "-q", "-m", message, env=env)

    def audit(self, **overrides):
        return inv.audit(self.root, args(**overrides))

    def close(self):
        self._tmp.cleanup()


class ModeTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.close()

    def test_no_agents_md_is_not_set_up(self):
        self.assertEqual(self.p.audit()["mode"], "not-set-up")

    def test_agents_md_without_marker_is_not_set_up(self):
        self.p.write("AGENTS.md", "# Something from /init\n")
        self.assertEqual(self.p.audit()["mode"], "not-set-up")

    def test_complete_harness_is_ready(self):
        self.p.harness()
        result = self.p.audit()
        self.assertEqual(result["mode"], "ready")
        self.assertEqual(result["setup"]["plan_path"], PLAN)
        self.assertEqual(result["broken_links"], [])
        self.assertEqual(result["orphans"], [])

    def test_missing_plan_or_tool_is_incomplete(self):
        self.p.harness()
        (self.p.root / "tools" / "harness.py").unlink()
        self.assertEqual(self.p.audit()["mode"], "incomplete")
        self.p.write("tools/harness.py", "")
        (self.p.root / PLAN).unlink()
        result = self.p.audit()
        self.assertEqual(result["mode"], "incomplete")
        self.assertIn("not found", inv.report(result, args()))

    def test_cli_exit_codes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(inv.main(["--root", str(self.p.root)]), 2)
        self.p.harness()
        with redirect_stdout(buf):
            self.assertEqual(inv.main(["--root", str(self.p.root)]), 0)


class LayerAndBudgetTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.p.harness()

    def tearDown(self):
        self.p.close()

    def test_layers(self):
        layers = {d["path"]: d["layer"] for d in self.p.audit()["docs"]}
        self.assertEqual(layers["AGENTS.md"], "L0")
        self.assertEqual(layers["docs/adr/0001-record-decisions-as-adrs.md"], "L2")
        self.assertNotIn(PLAN, layers)  # .omo/ is planner-owned and excluded from the doc audit

    def test_plan_is_measured_but_not_budgeted(self):
        result = self.p.audit()
        self.assertGreater(result["plan_tokens"], 0)
        self.assertEqual(result["budget"]["over"], 0)

    def test_over_budget(self):
        result = self.p.audit(l0_budget=100)
        self.assertGreater(result["budget"]["over"], 0)
        self.assertIn("OVER by", inv.report(result, args(l0_budget=100)))

    def test_template_section_fits_well_inside_budget(self):
        self.assertLess(self.p.audit()["budget"]["tokens"], 800)


class ReachabilityTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.p.harness(extra="\n| `docs/domain/gotchas.md` | When a tool fails oddly |\n"
                             "| `docs/rules/` | Before touching measured data |\n")
        self.p.write("docs/domain/gotchas.md", "# Gotchas\n")
        self.p.write("docs/rules/measurement-invariants.md", "# Rules\n")

    def tearDown(self):
        self.p.close()

    def test_directory_pointer_reaches_its_files(self):
        result = self.p.audit()
        self.assertEqual(result["orphans"], [])

    def test_orphan_and_broken_pointer(self):
        self.p.write("docs/domain/lonely.md", "# Nobody points here\n")
        self.p.write("docs/domain/gotchas.md", "See `docs/reference/missing.md`.\n")
        result = self.p.audit()
        self.assertEqual(result["orphans"], ["docs/domain/lonely.md"])
        self.assertEqual(result["broken_links"],
                         [{"from": "docs/domain/gotchas.md", "link": "docs/reference/missing.md"}])

    def test_missing_docs_directory_pointer_is_broken(self):
        self.p.write("AGENTS.md", (self.p.root / "AGENTS.md").read_text(encoding="utf-8")
                     + "| `docs/reference/` | When you need a settled value |\n")
        links = [b["link"] for b in self.p.audit()["broken_links"]]
        self.assertIn("docs/reference/", links)

    def test_fenced_examples_are_not_pointers(self):
        self.p.write("docs/domain/gotchas.md", "```\nsee `docs/nowhere.md`\n```\n")
        self.assertEqual(self.p.audit()["broken_links"], [])


class AdrAndStalenessTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.p.harness()

    def tearDown(self):
        self.p.close()

    def test_adr_problems(self):
        self.p.write("docs/adr/0002-model.md", "# 0002\n- Status: proposed\n")
        self.p.write("docs/adr/0002-other.md", "# dup\n- Status: accepted\n- Source: x\n")
        self.p.write("docs/adr/notes.md", "# bad name\n")
        adrs = self.p.audit()["adrs"]
        text = "\n".join(adrs["problems"])
        self.assertIn("0002-model.md: no '- Source:' line", text)
        self.assertIn("ADR number 0002 used by", text)
        self.assertIn("notes.md: name is not NNNN-<slug>.md", text)
        self.assertEqual(adrs["by_status"]["proposed"], 1)

    def test_old_adr_is_not_stale_but_old_doc_is(self):
        old = time.time() - 200 * 86400
        adr = self.p.root / "docs/adr/0001-record-decisions-as-adrs.md"
        doc = self.p.write("docs/architecture.md", "# Arch\n")
        self.p.write("AGENTS.md", (self.p.root / "AGENTS.md").read_text(encoding="utf-8")
                     + "| `docs/architecture.md` | Before changing module boundaries |\n")
        os.utime(adr, (old, old))
        os.utime(doc, (old, old))
        stale = [s["path"] for s in self.p.audit()["stale"]]
        self.assertEqual(stale, ["docs/architecture.md"])

    def test_verified_marker_resets_staleness(self):
        old = time.time() - 200 * 86400
        doc = self.p.write("docs/architecture.md",
                           f"# Arch\n<!-- verified: {time.strftime('%Y-%m-%d')} -->\n")
        os.utime(doc, (old, old))
        self.assertEqual(self.p.audit()["stale"], [])


class GitHarvestTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.p.git("init", "-q", "-b", "main")
        self.p.harness()
        self.p.commit("setup")
        self.setup_sha = self.p.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.p.close()

    def leaf(self, name, trailers):
        self.p.git("switch", "-q", "-c", f"feature/{name}")
        self.p.write(f"src/{name}.py", "x = 1\n")
        self.p.commit("checkpoint: work\n\n" + "\n".join(trailers), f"src/{name}.py")
        self.p.git("switch", "-q", "main")
        self.p.git("merge", "-q", "--no-ff", "-m", f"Merge feature/{name}", f"feature/{name}")

    def test_counts_merges_and_tagged_trailers(self):
        self.leaf("one", ["Next: a", "Learned: [gotcha] csv has units row",
                          "Learned: [candidate] mu0 fixed at 300 K"])
        self.leaf("two", ["Next: b", "Tried: power law — diverges"])
        h = self.p.audit()["harvest"]
        self.assertEqual(h["merges"], 2)
        self.assertEqual(h["trailers"]["Learned"], 2)
        self.assertEqual(h["learned_tags"], {"gotcha": 1, "candidate": 1})

    def test_counts_only_since_last_curated_commit(self):
        self.leaf("one", ["Next: a", "Learned: [gotcha] old"])
        curated = self.p.git("rev-parse", "HEAD").strip()
        self.p.write("docs/.curation-state.json",
                     '{"last_curated": "2026-09-01", "last_curated_commit": "%s"}' % curated)
        self.p.commit("curation state", "docs/.curation-state.json")
        self.leaf("two", ["Next: b", "Learned: [candidate] new"])
        h = self.p.audit()["harvest"]
        self.assertTrue(h["since_valid"])
        self.assertEqual(h["merges"], 1)
        self.assertEqual(h["learned_tags"], {"candidate": 1})

    def test_unknown_since_falls_back_with_warning(self):
        self.p.write("docs/.curation-state.json", '{"last_curated_commit": "deadbeef"}')
        result = self.p.audit()
        self.assertFalse(result["harvest"]["since_valid"])
        self.assertIn("not found", inv.report(result, args()))

    def test_ignored_plan_is_reported(self):
        self.p.git("rm", "-q", "--cached", PLAN)
        self.p.write(".gitignore", ".omo/\n")
        result = self.p.audit()
        self.assertTrue(result["setup"]["plan_ignored"])
        self.assertIn("git-ignored", inv.report(result, args()))

    def test_tracked_plan_is_versioned_even_if_folder_is_ignored(self):
        self.p.write(".gitignore", ".omo/\n")
        self.assertFalse(self.p.audit()["setup"]["plan_ignored"])

    def test_gate_file_open_too_long(self):
        self.p.write("tests/gates/test_old.py",
                     "import pytest\n@pytest.mark.xfail(strict=True, reason='gate: x')\n"
                     "def test_x():\n    assert False\n")
        self.p.write("tests/gates/test_done.py", "def test_y():\n    assert True\n")
        old = "2025-01-01T12:00:00"
        self.p.commit("old gates", "tests/gates/test_old.py", "tests/gates/test_done.py",
                      env={"GIT_AUTHOR_DATE": old, "GIT_COMMITTER_DATE": old})
        stale = self.p.audit()["stale_gates"]
        self.assertEqual([g["path"] for g in stale], ["tests/gates/test_old.py"])


GOOD_THEORY = """# Theory — demo

## Model overview

Field-dependent mobility with velocity saturation.

## Equations

### EQ-mu-field — field-dependent mobility

$$ \\mu(E) = \\mu_0 / (1 + E/E_c) $$

- Symbols and units: mu [cm2/Vs], E [kV/cm]
- Assumptions: steady state, uniform field
- Valid for: 300 K, E < 50 kV/cm
- Source: [R1] eq. (3), p. 2193
- Implementation: `src/mobility.py::mu`
- Verification: `tests/gates/test_fit.py::test_low_field_limit`
- Status: validated

## References

- [R1] A. Author and B. Author, "An example mobility model," J. Example 1, 2190 (2000).
  DOI: 10.5555/example.0001 — checked: user 2026-09-26
"""


class TheoryTests(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.p.harness()
        self.p.write("src/mobility.py", "def mu(E, mu0, Ec):\n    return mu0 / (1 + E / Ec)\n")
        self.p.write("tests/gates/test_fit.py", "def test_low_field_limit():\n    pass\n")

    def tearDown(self):
        self.p.close()

    def theory(self, text):
        self.p.write("docs/theory.md", text)
        return self.p.audit()["theory"]

    def test_absent_theory_is_not_a_problem(self):
        self.assertFalse(self.p.audit()["theory"]["exists"])

    def test_complete_theory_has_no_problems(self):
        t = self.theory(GOOD_THEORY)
        self.assertEqual((t["equations"], t["references"]), (1, 1))
        self.assertEqual(t["problems"], [])
        self.assertEqual(t["tbd"], [])

    def test_identifier_without_checked_is_flagged(self):
        t = self.theory(GOOD_THEORY.replace(" — checked: user 2026-09-26", ""))
        self.assertIn("[R1]: identifier without 'checked: pdf | user | online'", t["problems"])

    def test_malformed_doi_and_missing_identifier(self):
        text = GOOD_THEORY.replace("10.5555/example.0001", "10.11/x") + (
            "- [R2] Someone, \"A paper,\" J. Somewhere 1, 1 (2020).\n")
        t = self.theory(text)
        joined = "\n".join(t["problems"])
        self.assertIn("[R1]: malformed DOI `10.11/x`", joined)
        self.assertIn("[R2]: no DOI, arXiv, ISBN, or Internal identifier", joined)
        self.assertEqual(t["unused_references"], ["R2"])

    def test_tbd_is_open_not_a_problem(self):
        text = GOOD_THEORY.replace("- Source: [R1] eq. (3), p. 2193",
                                   "- Source: adapted from a textbook,\n  [TBD: source]")
        t = self.theory(text)
        self.assertIn("EQ-mu-field: source", t["tbd"])
        self.assertEqual(t["problems"], [])

    def test_uncited_source_and_undefined_reference(self):
        text = GOOD_THEORY.replace("[R1] eq. (3), p. 2193", "Smith's classic paper")
        t = self.theory(text.replace("- Verification:", "- Note: [R9]\n- Verification:"))
        joined = "\n".join(t["problems"])
        self.assertIn("EQ-mu-field: source cites no [Rn] reference", joined)

    def test_cited_but_not_listed(self):
        t = self.theory(GOOD_THEORY.replace("[R1] eq. (3)", "[R1][R3] eq. (3)"))
        self.assertIn("[R3] is cited but not listed under References", t["problems"])

    def test_code_links_must_exist(self):
        text = (GOOD_THEORY.replace("src/mobility.py::mu", "src/mobility.py::mobility")
                .replace("test_fit.py::", "test_missing.py::"))
        joined = "\n".join(self.theory(text)["problems"])
        self.assertIn("`src/mobility.py::mobility` not defined", joined)
        self.assertIn("Verification file `tests/gates/test_missing.py` not found", joined)

    def test_duplicate_doi_and_missing_fields(self):
        text = GOOD_THEORY.replace("- Status: validated\n", "") + (
            "- [R2] Copy. DOI: 10.5555/example.0001 — checked: pdf\n")
        joined = "\n".join(self.theory(text)["problems"])
        self.assertIn("EQ-mu-field: no '- Status:' line", joined)
        self.assertIn("appears in [R1], [R2]", joined)

    def test_unfilled_template_is_flagged(self):
        template = (ROOT / "skills" / "session-start" / "templates" / "theory.md").read_text(
            encoding="utf-8")
        t = self.theory(template)
        self.assertTrue(any("placeholder" in p for p in t["problems"]))
        self.assertEqual(t["missing_sections"], [])

    def test_report_section(self):
        self.theory(GOOD_THEORY.replace(" — checked: user 2026-09-26", ""))
        text = inv.report(self.p.audit(), args())
        self.assertIn("## 8. Theory document", text)
        self.assertIn("identifier without", text)


class TokenTests(unittest.TestCase):
    def test_estimate_tokens_mixed_text(self):
        self.assertEqual(inv.estimate_tokens("abcd" * 10), 10)
        self.assertEqual(inv.estimate_tokens("가나다"), 2)


if __name__ == "__main__":
    unittest.main()
