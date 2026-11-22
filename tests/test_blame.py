import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from todomold.blame import blame


def _git(repo: Path, *args, author="Alice", date=None):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "a@example.com",
        "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": "a@example.com",
    })
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


class TestBlame(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        _git(self.root, "init", "-q")
        (self.root / "a.py").write_text("old = 1  # TODO: old\nold = 2\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "first", author="Alice",
             date="2024-06-01T00:00:00 +0000")
        (self.root / "a.py").write_text("old = 1  # TODO: old\nold = 2\nnew = 3  # FIXME: later\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "second", author="Bob",
             date="2026-01-01T00:00:00 +0000")

    def test_authors_and_dates(self):
        lines = blame(self.root, "a.py")
        self.assertEqual(lines[1].author, "Alice")
        self.assertEqual(lines[1].time, 1717200000)  # 2024-06-01
        self.assertEqual(lines[3].author, "Bob")
        self.assertEqual(lines[3].time, 1767225600)  # 2026-01-01

    def test_uncommitted_line_keeps_current_time(self):
        (self.root / "a.py").write_text(
            "old = 1  # TODO: old\nold = 2\nnew = 3  # FIXME: later\nfresh = 4  # TODO: now\n"
        )
        lines = blame(self.root, "a.py")
        self.assertEqual(lines[4].author, "Not Committed Yet")
        self.assertGreater(lines[4].time, 0)

    def test_untracked_file_returns_empty(self):
        (self.root / "orphan.txt").write_text("TODO nothing\n")
        self.assertEqual(blame(self.root, "orphan.txt"), {})

    def test_missing_file_returns_empty(self):
        self.assertEqual(blame(self.root, "ghost.txt"), {})


if __name__ == "__main__":
    unittest.main()
