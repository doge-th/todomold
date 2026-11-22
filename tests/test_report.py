import json
import unittest

from todomold.report import Analysis, Entry, bar, fmt_age, fmt_date, render_json, render_markdown, render_table

NOW = 1_800_000_000  # 2027-01


class _Opts:
    top = 10


def _analysis():
    res = Analysis(root="/tmp/repo")
    res.entries = [
        Entry("src/old.py", 10, "FIXME", "rewrite", "Alice", NOW - 800 * 86400),
        Entry("src/new.py", 3, "TODO", "add tests", "Bob", NOW - 5 * 86400),
        Entry("src/mid.py", 7, "TODO", "cleanup", "Alice", NOW - 100 * 86400),
        Entry("misc.txt", 1, "HACK", "why", None, None),  # unknown origin
    ]
    return res


class TestFormatters(unittest.TestCase):
    def test_fmt_age(self):
        self.assertEqual(fmt_age(NOW - 3600, now=NOW), "today")
        self.assertEqual(fmt_age(NOW - 3 * 86400, now=NOW), "3d")
        self.assertEqual(fmt_age(NOW - 100 * 86400, now=NOW), "3mo")
        self.assertEqual(fmt_age(NOW - 800 * 86400, now=NOW), "2.2y")
        self.assertEqual(fmt_age(None), "?")
        self.assertEqual(fmt_age(0), "?")

    def test_fmt_date(self):
        self.assertEqual(fmt_date(1717200000), "2024-06")
        self.assertEqual(fmt_date(None), "?")

    def test_bar_clamps(self):
        self.assertEqual(bar(2.0), "█" * 14)
        self.assertEqual(bar(0.5, width=10), "█████░░░░░")


class TestAggregation(unittest.TestCase):
    def test_oldest_puts_unknown_last(self):
        ranked = _analysis().oldest()
        self.assertEqual(ranked[0].path, "src/old.py")
        self.assertEqual(ranked[-1].path, "misc.txt")

    def test_by_tag_and_author(self):
        res = _analysis()
        self.assertEqual(res.by_tag(), [("TODO", 2), ("FIXME", 1), ("HACK", 1)])
        self.assertEqual(res.by_author(), [("Alice", 2), ("Bob", 1)])


class TestRenderers(unittest.TestCase):
    def test_table_sections(self):
        out = render_table(_analysis(), _Opts)
        for section in ("mold ranking", "Who owes the most", "By tag"):
            self.assertIn(section, out)
        self.assertIn("src/old.py:10", out)
        self.assertIn("[FIXME] rewrite", out)
        self.assertIn("Alice", out)

    def test_empty_repo_is_encouraging(self):
        out = render_table(Analysis(root="/tmp/repo"), _Opts)
        self.assertIn("No mold here", out)

    def test_json_structure(self):
        doc = json.loads(render_json(_analysis(), _Opts))
        self.assertEqual(doc["tool"], "todomold")
        self.assertEqual(doc["markers"], 4)
        self.assertEqual(doc["entries"][0]["path"], "src/old.py")  # oldest first
        self.assertEqual(doc["by_author"], {"Alice": 2, "Bob": 1})
        self.assertIn("age_days", doc["entries"][0])

    def test_markdown_escapes_pipes(self):
        res = Analysis(root="/tmp/repo")
        res.entries = [Entry("a.py", 1, "TODO", "do | this", "Alice", NOW)]
        out = render_markdown(res, _Opts)
        self.assertIn("do \\| this", out)


if __name__ == "__main__":
    unittest.main()
