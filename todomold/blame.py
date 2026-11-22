"""git blame porcelain parsing: who wrote each line, and when."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LineOrigin:
    author: str
    time: int  # unix timestamp of the authoring commit


def _is_header(first: str, parts: list[str]) -> bool:
    """Porcelain block header: '<40-hex sha> <orig> <final> [<count>]'.
    Also emitted for re-used shas as '<sha> <orig> <final>' (one line)."""
    return len(first) == 40 and len(parts) >= 3 and parts[1].isdigit() \
        and parts[2].isdigit() and all(c in "0123456789abcdef" for c in first)


def blame(root: Path, rel_path: str) -> dict[int, LineOrigin]:
    """Final line number -> (author, unix time) for one tracked file.

    An empty dict means blame failed (e.g. untracked file) — callers keep
    the entry but leave its origin unknown. Uncommitted lines carry git's
    "Not Committed Yet" author and the current time.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "blame", "--porcelain", "--", rel_path],
        capture_output=True,
    )
    if proc.returncode != 0:
        return {}

    out: dict[int, LineOrigin] = {}
    meta: dict[str, tuple[str, int]] = {}  # sha -> (author, time)
    sha = None
    author = "unknown"
    when = 0
    final_line: int | None = None

    def flush():
        if final_line is not None:
            out[final_line] = LineOrigin(author, when)

    for raw in proc.stdout.decode("utf-8", "replace").splitlines():
        if raw.startswith("\t"):
            flush()  # every porcelain block ends with its source-text line
            final_line = None
            continue
        parts = raw.split(" ")
        if _is_header(parts[0], parts):
            flush()  # blocks without a text line (defensive)
            sha = parts[0]
            final_line = int(parts[2])
            # Repeated commits emit only the short header — reuse metadata.
            author, when = meta.get(sha, ("unknown", 0))
        elif raw.startswith("author ") and final_line is not None:
            author = raw[len("author "):]
        elif raw.startswith("author-time ") and final_line is not None:
            try:
                when = int(raw[len("author-time "):])
            except ValueError:
                when = 0
            if sha:
                meta[sha] = (author, when)
    flush()  # defensive: a trailing block without its text line
    return out
