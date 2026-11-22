"""Aggregation and the three report renderers (table/json/markdown)."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

from . import __version__
from .scan import Marker


@dataclass
class Entry:
    path: str
    line: int
    tag: str
    text: str
    author: str | None = None
    date: int | None = None  # unix ts of the authoring commit; None if unknown

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass
class Analysis:
    root: str
    entries: list[Entry] = field(default_factory=list)

    def oldest(self) -> list[Entry]:
        """Dated entries, oldest first. Unknown-age entries go last."""
        return sorted(
            self.entries,
            key=lambda e: (e.date is None, e.date if e.date is not None else 0),
        )

    def by_tag(self) -> list[tuple[str, int]]:
        return sorted(Counter(e.tag for e in self.entries).items(),
                      key=lambda kv: -kv[1])

    def by_author(self) -> list[tuple[str, int]]:
        return sorted(
            Counter(e.author for e in self.entries if e.author).items(),
            key=lambda kv: -kv[1],
        )


def annotate(root, markers: list[Marker], blame_fn) -> Analysis:
    """Attach author/date from a blame_fn(path) -> {line: LineOrigin} lookup."""
    analysis = Analysis(root=str(root))
    cache: dict[str, dict] = {}
    for m in markers:
        origin = cache.get(m.path)
        if origin is None:
            origin = cache[m.path] = blame_fn(m.path)
        hit = origin.get(m.line)
        analysis.entries.append(Entry(
            m.path, m.line, m.tag, m.text,
            author=hit.author if hit else None,
            date=hit.time if hit else None,
        ))
    return analysis


# ---------------------------------------------------------------- formatting

def _ansi_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


class Ansi:
    def __init__(self, enabled: bool = None):
        self.on = _ansi_enabled() if enabled is None else enabled

    def _wrap(self, code: int, s: str) -> str:
        return f"\x1b[{code}m{s}\x1b[0m" if self.on else s

    def bold(self, s): return self._wrap(1, s)
    def dim(self, s): return self._wrap(2, s)
    def red(self, s): return self._wrap(31, s)
    def green(self, s): return self._wrap(32, s)
    def yellow(self, s): return self._wrap(33, s)
    def cyan(self, s): return self._wrap(36, s)


def fmt_age(unix_ts: int | None, now: int | None = None) -> str:
    if not unix_ts:
        return "?"
    now = now if now is not None else int(time.time())
    days = max(0, (now - unix_ts) // 86400)
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d"
    if days < 365:
        return f"{days // 30}mo"
    return f"{days / 365:.1f}y"


def fmt_date(unix_ts: int | None) -> str:
    if not unix_ts:
        return "?"
    return time.strftime("%Y-%m", time.gmtime(unix_ts))


def bar(frac: float, width: int = 14) -> str:
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


def _mold_color(a: Ansi, age_days_ceil: float):
    if age_days_ceil >= 365:
        return a.red
    if age_days_ceil >= 90:
        return a.yellow
    return a.cyan


def render_table(res: Analysis, opts) -> str:
    a = Ansi()
    out = []
    blamed = sum(1 for e in res.entries if e.author)
    out.append(a.bold(f"todomold v{__version__}")
               + a.dim(f"  ·  {res.root}  ·  {len(res.entries)} markers"
                       f" · {blamed} blamed"))
    out.append("")
    if not res.entries:
        out.append(a.green("No mold here — not a single TODO/FIXME/HACK/XXX."))
        return "\n".join(out)

    oldest = res.oldest()[: opts.top]
    max_age = max((e.date for e in oldest if e.date), default=None)
    now = int(time.time())
    out.append(a.cyan(f"The mold ranking (oldest first) — top {opts.top}"))
    for e in oldest:
        age_days = (now - e.date) / 86400 if e.date else -1
        frac = (age_days / (max_age / 86400)) if max_age and e.date else 0.0
        paint = _mold_color(a, age_days)
        age = paint(f"{fmt_age(e.date):>6}")
        bar_row = paint(bar(frac))
        who = f"{e.author}, {fmt_date(e.date)}" if e.author else "uncommitted/unknown"
        out.append(
            f"  {age}  {bar_row}  {a.bold(e.where)}  [{e.tag}] {e.text}"
            f"  {a.dim(f'({who})')}"
        )

    out.append("")
    out.append(a.cyan("Who owes the most"))
    width = max((len(name) for name, _ in res.by_author()[: opts.top]), default=1)
    for name, count in res.by_author()[: opts.top]:
        share = count / max(blamed, 1)
        out.append(f"  {name:<{width}}  {count:>4}  {bar(share)}  {share:.0%}")

    out.append("")
    out.append(a.cyan("By tag"))
    for tag, count in res.by_tag():
        out.append(f"  {tag:<8} {count:>4}  {bar(count / max(len(res.entries), 1))}")
    return "\n".join(out)


def render_json(res: Analysis, opts) -> str:
    doc = {
        "tool": "todomold",
        "version": __version__,
        "root": res.root,
        "markers": len(res.entries),
        "entries": [
            {
                "path": e.path,
                "line": e.line,
                "tag": e.tag,
                "text": e.text,
                "author": e.author,
                "date": e.date,
                "age_days": (int((time.time() - e.date) / 86400)
                             if e.date else None),
            }
            for e in res.oldest()
        ],
        "by_tag": dict(res.by_tag()),
        "by_author": dict(res.by_author()),
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


def render_markdown(res: Analysis, opts) -> str:
    lines = [
        f"## todomold — `{res.root}`",
        "",
        f"**{len(res.entries)} markers**",
        "",
        "| age | where | tag | text | author |",
        "|---:|---|---|---|---|",
    ]
    for e in res.oldest()[: opts.top]:
        who = e.author or "?"
        text = e.text.replace("|", "\\|") or "—"
        lines.append(
            f"| {fmt_age(e.date)} | `{e.where}` | {e.tag} | {text} | {who} |"
        )
    return "\n".join(lines)
