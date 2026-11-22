import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from todomold.scan import build_pattern, scan


def _git(repo: Path, *args):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "Tester", "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "Tester", "GIT_COMMITTER_EMAIL": "t@example.com",
    })
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _repo():
    root = Path(tempfile.mkdtemp())
    _git(root, "init", "-q")
    (root / "a.py").write_text("def f():\n    pass  # TODO: finish this\n")
    (root / "b.js").write_text("// FIXME: crash on empty input\nlet x = 1;\n")
    (root / "notes.txt").write_text("my todo list for groceries\n")
    (root / "img.png").write_bytes(b"\x89PNG\x00\x00 TODO not seen")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    return root


class TestPattern(unittest.TestCase):
    def test_matches_tags(self):
        p = build_pattern(["TODO", "FIXME"])
        self.assertTrue(p.search("x = 1  # TODO: later"))
        self.assertTrue(p.search("//FIXME now"))

    def test_word_boundary(self):
        p = build_pattern(["TODO"])
        self.assertFalse(p.search("my todo list"))  # lowercase
        self.assertFalse(p.search("autodoodles"))  # substring


class TestScan(unittest.TestCase):
    def test_finds_markers(self):
        markers = scan(_repo(), ["TODO", "FIXME", "HACK", "XXX"])
        self.assertEqual(len(markers), 2)
        self.assertEqual(markers[0].path, "a.py")
        self.assertEqual(markers[0].line, 2)
        self.assertEqual(markers[0].tag, "TODO")
        self.assertEqual(markers[0].text, "finish this")
        self.assertEqual({m.tag for m in markers}, {"TODO", "FIXME"})

    def test_custom_tags(self):
        markers = scan(_repo(), ["NOTE"])
        self.assertEqual(markers, [])

    def test_ignore_case(self):
        markers = scan(_repo(), ["TODO"], ignore_case=True)
        self.assertEqual([m.tag for m in markers], ["TODO", "TODO"])

    def test_excludes_glob(self):
        markers = scan(_repo(), ["TODO", "FIXME"], excludes=["*.js"])
        self.assertEqual([m.path for m in markers], ["a.py"])

    def test_not_a_repo_raises(self):
        with self.assertRaises(RuntimeError):
            scan(Path(tempfile.mkdtemp()), ["TODO"])


if __name__ == "__main__":
    unittest.main()
