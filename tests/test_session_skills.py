"""Budget and contract checks for the v3.1 session skills.

The session skills are loaded into the same context window they protect, so their size is
part of the design (DESIGN.md, principle 9). Standard library only.
"""

import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "context-curation" / "scripts"))

from docs_inventory import estimate_tokens  # noqa: E402

SKILLS = ROOT / "skills"
START = SKILLS / "session-start"
SKILL_BUDGET = 1500
AGENTS_SECTION_BUDGET = 700
POSIX_ONLY = re.compile(r"\b(grep|sed|awk|wc)\b")
FORBIDDEN_GIT = re.compile(r"git (add -A|add \.|push|rebase|reset|stash|commit --amend)")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def session_skills():
    return sorted(SKILLS.glob("session-*/SKILL.md"))


class SkillBudgetTests(unittest.TestCase):
    def test_all_three_session_skills_exist(self):
        names = {p.parent.name for p in session_skills()}
        self.assertEqual(names, {"session-start", "session-checkpoint", "session-end"})

    def test_each_session_skill_is_under_budget(self):
        for path in session_skills():
            with self.subTest(skill=path.parent.name):
                self.assertLessEqual(estimate_tokens(read(path)), SKILL_BUDGET)

    def test_frontmatter_name_matches_folder(self):
        for path in session_skills():
            with self.subTest(skill=path.parent.name):
                match = re.search(r"^name:\s*(\S+)", read(path), re.MULTILINE)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), path.parent.name)

    def test_no_posix_only_commands(self):
        for path in session_skills():
            with self.subTest(skill=path.parent.name):
                self.assertIsNone(POSIX_ONLY.search(read(path)))

    def test_forbidden_git_operations_appear_only_as_prohibitions(self):
        for path in session_skills():
            for line in read(path).splitlines():
                if FORBIDDEN_GIT.search(line):
                    with self.subTest(skill=path.parent.name, line=line):
                        self.assertRegex(line, r"\b(Never|never|Do not|not)\b")

    def test_no_prose_state_files_remain(self):
        for path in session_skills():
            text = read(path)
            with self.subTest(skill=path.parent.name):
                self.assertNotIn("WORKING.md", text)
                self.assertNotIn("SESSION-LOG", text)


class TemplateTests(unittest.TestCase):
    def test_agents_section_markers_and_budget(self):
        text = read(START / "templates" / "agents-section.md")
        self.assertEqual(text.count("<!-- memory-harness:start -->"), 1)
        self.assertEqual(text.count("<!-- memory-harness:end -->"), 1)
        self.assertLess(text.index("memory-harness:start"), text.index("memory-harness:end"))
        self.assertIn("python tools/harness.py status", text)
        self.assertIn("<plan-path>", text)
        self.assertIn("strict=True", text)
        self.assertLessEqual(estimate_tokens(text), AGENTS_SECTION_BUDGET)

    def test_gate_template_uses_strict_xfail_with_raises(self):
        text = read(START / "templates" / "gate_test.py")
        self.assertIn("strict=True, raises=(AssertionError, NotImplementedError)", text)
        self.assertIn('reason="gate:', text)
        self.assertIn('reason="blocked:', text)

    def test_adr_template_sections(self):
        text = read(START / "templates" / "adr-0001.md")
        for part in ("- Status:", "- Source:", "## Context", "## Decision",
                     "## Alternatives considered", "## Consequences"):
            with self.subTest(part=part):
                self.assertIn(part, text)

    def test_skills_reference_files_that_exist(self):
        start = read(START / "SKILL.md")
        for rel in ("templates/agents-section.md", "templates/gate_test.py",
                    "templates/adr-0001.md", "scripts/harness.py"):
            with self.subTest(ref=rel):
                self.assertIn(rel, start)
                self.assertTrue((START / rel).is_file())

    def test_harness_script_is_stdlib_only(self):
        tree = ast.parse(read(START / "scripts" / "harness.py"))
        stdlib = {"__future__", "argparse", "ast", "json", "re", "subprocess", "sys", "pathlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            for name in names:
                with self.subTest(module=name):
                    self.assertIn(name, stdlib)

    def test_checkpoint_trailers_match_harness_parser(self):
        sys.path.insert(0, str(START / "scripts"))
        import harness
        text = read(SKILLS / "session-checkpoint" / "SKILL.md")
        for key in harness.TRAILER_KEYS:
            with self.subTest(trailer=key):
                self.assertIn(f"`{key}:`", text)


if __name__ == "__main__":
    unittest.main()
