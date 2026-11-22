import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from todomold import __version__
from todomold.cli import main


def _git(repo: Path, *args):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "Alice", "GIT_AUTHOR_EMAIL": "a@example.com",
        "GIT_COMMITTER_NAME": "Alice", "GIT_COMMITTER_EMAIL": "a@example.com",
    })
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _repo():
    root = Path(tempfile.mkdtemp())
    _git(root, "init", "-q")
    (root / "a.py").write_text("# TODO: first\nx = 1\n")
    (root / "b.py").write_text("# FIXME: second\n# TODO: third\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    return root


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = _repo()

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_table_report(self):
        code, out, _ = self._run([str(self.root)])
        self.assertEqual(code, 0)
        for section in ("mold ranking", "Who owes the most", "By tag"):
            self.assertIn(section, out)
        self.assertIn("3 markers", out)
        self.assertIn("a.py:1", out)
        self.assertIn("[TODO] first", out)
        self.assertIn("Alice", out)

    def test_json_report(self):
        _, out, _ = self._run(["--json", str(self.root)])
        doc = json.loads(out)
        self.assertEqual(doc["tool"], "todomold")
        self.assertEqual(doc["version"], __version__)
        self.assertEqual(doc["markers"], 3)
        self.assertEqual(len(doc["entries"]), 3)
        self.assertTrue(all(e["author"] == "Alice" for e in doc["entries"]))

    def test_no_blame_leaves_origin_unknown(self):
        _, out, _ = self._run(["--json", "--no-blame", str(self.root)])
        doc = json.loads(out)
        self.assertTrue(all(e["author"] is None for e in doc["entries"]))

    def test_tag_filter_narrows(self):
        _, out, _ = self._run(["--json", "--tag", "FIXME", str(self.root)])
        doc = json.loads(out)
        self.assertEqual(doc["markers"], 1)
        self.assertEqual(doc["entries"][0]["tag"], "FIXME")

    def test_markdown_report(self):
        _, out, _ = self._run(["--markdown", str(self.root)])
        self.assertIn("## todomold", out)
        self.assertIn("| age | where | tag | text | author |", out)

    def test_empty_repo_encourages(self):
        empty = Path(tempfile.mkdtemp())
        _git(empty, "init", "-q")
        (empty / "clean.py").write_text("print('ok')\n")
        _git(empty, "add", "-A")
        _git(empty, "commit", "-q", "-m", "clean")
        _, out, _ = self._run([str(empty)])
        self.assertIn("No mold here", out)

    def test_non_git_dir_fails_cleanly(self):
        code, _, err = self._run([tempfile.mkdtemp()])
        self.assertEqual(code, 1)
        self.assertIn("not a git repository", err)

    def test_missing_dir_fails_cleanly(self):
        code, _, err = self._run(["/nonexistent/no-repo"])
        self.assertEqual(code, 1)
        self.assertIn("not a directory", err)

    def test_version_flag(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
