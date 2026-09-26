"""Keep the usage guides honest: links, repository paths, and tool commands must exist.

The guides describe what the skills and tools do. When a skill or a command changes and the guide
does not, these tests fail. Standard library only.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "session-start" / "scripts"))

import harness  # noqa: E402

GUIDES = [ROOT / "docs" / "USAGE.md", ROOT / "docs" / "USAGE.ko.md"]
READMES = [ROOT / "README.md", ROOT / "README.ko.md"]


def slug(heading: str) -> str:
    """GitHub-style anchor: lowercase, drop punctuation, spaces become dashes."""
    text = heading.strip().lower()
    text = "".join(ch for ch in text if ch.isalnum() or ch in "-_ ")
    return text.replace(" ", "-")


def strip_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


class GuideTests(unittest.TestCase):
    def test_guides_exist_and_are_linked_from_readmes(self):
        for guide in GUIDES:
            self.assertTrue(guide.is_file(), guide)
        self.assertIn("docs/USAGE.md", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("docs/USAGE.ko.md", (ROOT / "README.ko.md").read_text(encoding="utf-8"))

    def test_internal_anchors_resolve(self):
        for guide in GUIDES:
            text = guide.read_text(encoding="utf-8")
            anchors = {slug(h) for h in re.findall(r"^#{1,6}\s+(.+)$", strip_code(text), re.M)}
            for target in re.findall(r"\]\(#([^)]+)\)", text):
                with self.subTest(guide=guide.name, anchor=target):
                    self.assertIn(target, anchors)

    def test_both_languages_have_the_same_sections(self):
        counts = [len(re.findall(r"^## ", strip_code(g.read_text(encoding="utf-8")), re.M))
                  for g in GUIDES]
        self.assertEqual(counts[0], counts[1])

    def test_repository_paths_exist(self):
        pattern = re.compile(r"skills[\\/][\w./\\-]+\.(?:md|py)")
        for guide in GUIDES + READMES:
            for ref in set(pattern.findall(guide.read_text(encoding="utf-8"))):
                with self.subTest(file=guide.name, path=ref):
                    self.assertTrue((ROOT / ref.replace("\\", "/")).is_file())

    def test_harness_commands_and_flags_exist(self):
        commands = {"status": {"--base", "--json"}, "gates": {"--all", "--json"},
                    "harvest": {"--since", "--keys", "--json"}}
        pattern = re.compile(r"harness\.py[ \t]+(\w+)((?:[ \t]+--[\w-]+(?:[ \t]+[^\s`#-][^\s`#]*)?)*)")
        for guide in GUIDES + READMES:
            for command, rest in pattern.findall(guide.read_text(encoding="utf-8")):
                with self.subTest(file=guide.name, command=command):
                    self.assertIn(command, commands)
                    for flag in re.findall(r"--[\w-]+", rest):
                        self.assertIn(flag, commands[command])

    def test_documented_trailers_match_the_tool(self):
        for guide in GUIDES:
            text = guide.read_text(encoding="utf-8")
            for key in harness.TRAILER_KEYS:
                with self.subTest(guide=guide.name, trailer=key):
                    self.assertIn(f"`{key}:`", text)

    def test_guides_show_no_real_looking_doi(self):
        real = re.compile(r"\b10\.\d{4,9}/(?!x{3,})[\w.()-]+")
        for guide in GUIDES:
            with self.subTest(guide=guide.name):
                self.assertIsNone(real.search(guide.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
