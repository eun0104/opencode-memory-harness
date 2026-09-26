"""Budget and contract checks for the v3 session skills.

The session skills are loaded into the same context window they protect, so their size is
part of the design (DESIGN.md, principle 8). Standard library only.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "context-curation" / "scripts"))

from docs_inventory import estimate_tokens  # noqa: E402

SKILLS = ROOT / "skills"
SKILL_BUDGET = 1500
AGENTS_SECTION_BUDGET = 600
WORKING_TEMPLATE_BUDGET = 400
POSIX_ONLY = re.compile(r"\b(grep|sed|awk|wc)\b")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SkillBudgetTests(unittest.TestCase):
    def session_skills(self):
        return sorted(SKILLS.glob("session-*/SKILL.md"))

    def test_session_skills_exist(self):
        names = {p.parent.name for p in self.session_skills()}
        self.assertTrue({"session-start", "session-checkpoint"} <= names, names)

    def test_each_session_skill_is_under_budget(self):
        for path in self.session_skills():
            with self.subTest(skill=path.parent.name):
                self.assertLessEqual(estimate_tokens(read(path)), SKILL_BUDGET)

    def test_frontmatter_name_matches_folder(self):
        for path in self.session_skills():
            with self.subTest(skill=path.parent.name):
                match = re.search(r"^name:\s*(\S+)", read(path), re.MULTILINE)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), path.parent.name)

    def test_no_posix_only_commands(self):
        for path in self.session_skills():
            with self.subTest(skill=path.parent.name):
                self.assertIsNone(POSIX_ONLY.search(read(path)))


class TemplateTests(unittest.TestCase):
    def test_agents_section_markers_and_budget(self):
        text = read(SKILLS / "session-start" / "templates" / "agents-section.md")
        self.assertEqual(text.count("<!-- memory-harness:start -->"), 1)
        self.assertEqual(text.count("<!-- memory-harness:end -->"), 1)
        self.assertLess(text.index("memory-harness:start"), text.index("memory-harness:end"))
        self.assertIn("docs/handoff/WORKING.md", text)
        self.assertIn("<plan-path>", text)
        self.assertLessEqual(estimate_tokens(text), AGENTS_SECTION_BUDGET)

    def test_working_template_sections_and_budget(self):
        text = read(SKILLS / "session-checkpoint" / "templates" / "WORKING.md")
        for heading in ("## Goal", "## Gates", "## Next action", "## Decisions this session",
                        "## Do not repeat", "## In flight", "## Open questions"):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)
        self.assertIn("CHECK:", text)
        self.assertIn("EVIDENCE:", text)
        self.assertLessEqual(estimate_tokens(text), WORKING_TEMPLATE_BUDGET)

    def test_skills_reference_existing_templates(self):
        start = read(SKILLS / "session-start" / "SKILL.md")
        self.assertIn("templates/agents-section.md", start)
        checkpoint = read(SKILLS / "session-checkpoint" / "SKILL.md")
        self.assertIn("templates/WORKING.md", checkpoint)


if __name__ == "__main__":
    unittest.main()
