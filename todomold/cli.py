"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .blame import blame
from .report import annotate, render_json, render_markdown, render_table
from .scan import DEFAULT_TAGS, scan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="todomold",
        description="Every TODO/FIXME/HACK in your repo, with who wrote it "
                    "and how long it has been rotting — ranked by age.",
        epilog="examples:  todomold .  ·  todomold src --tag FIXME --tag HACK  ·  "
               "todomold . --json",
    )
    p.add_argument("path", nargs="?", default=".",
                   help="repository to analyze (default: .)")
    p.add_argument("--top", type=int, default=10, metavar="N",
                   help="show N entries per section (default 10)")
    p.add_argument("--tag", action="append", metavar="TAG",
                   help="marker to hunt (repeatable; default: TODO FIXME HACK XXX)")
    p.add_argument("--ignore-case", action="store_true",
                   help="also match lowercase todo/fixme ...")
    p.add_argument("--exclude", action="append", metavar="GLOB",
                   help="extra path glob to skip (repeatable)")
    p.add_argument("--no-blame", action="store_true",
                   help="skip git blame: much faster on big repos, no author/age")
    p.add_argument("--json", dest="fmt", action="store_const", const="json",
                   help="machine-readable JSON output")
    p.add_argument("--markdown", "--md", dest="fmt", action="store_const",
                   const="markdown", help="markdown output for issues/PRs")
    p.add_argument("--version", action="version",
                   version=f"todomold {__version__}")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    opts = parser.parse_args(argv)
    if opts.top < 0:
        parser.error("--top must be >= 0")

    root = Path(opts.path)
    if not root.is_dir():
        print(f"todomold: not a directory: {opts.path}", file=sys.stderr)
        return 1

    tags = opts.tag if opts.tag else list(DEFAULT_TAGS)
    try:
        markers = scan(root, tags, opts.ignore_case, opts.exclude)
    except RuntimeError as e:
        print(f"todomold: {e}", file=sys.stderr)
        return 1

    if opts.no_blame:
        res = annotate(root, markers, lambda _path: {})
    else:
        res = annotate(root, markers, lambda path: blame(root, path))

    renderer = {"table": render_table, "json": render_json,
                "markdown": render_markdown}[opts.fmt or "table"]
    print(renderer(res, opts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
