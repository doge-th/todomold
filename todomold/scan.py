"""Marker scanning: find TODO/FIXME/... lines in tracked files."""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TAGS = ("TODO", "FIXME", "HACK", "XXX")

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".icns", ".tiff",
    ".svg",
    ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".mp4", ".mov", ".avi",
    ".mkv", ".webm",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".db", ".sqlite", ".sqlite3", ".parquet", ".pickle", ".pkl",
    ".pyc", ".pyo", ".wasm", ".onnx", ".pt", ".pth", ".safetensors", ".gguf",
    ".lock",
}


@dataclass
class Marker:
    path: str  # relative, posix-style
    line: int  # 1-based
    tag: str
    text: str  # what follows the marker, trimmed


def build_pattern(tags: list[str], ignore_case: bool = False) -> re.Pattern:
    """Word-boundary pattern that matches any of the tags, then punctuation."""
    escaped = "|".join(re.escape(t) for t in tags)
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile(rf"\b(?:{escaped})\b:?", flags)


def tracked_files(root: Path, extra_excludes: list[str]) -> list[str]:
    """Tracked + untracked-but-not-ignored text files, posix-style relative."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z",
         "--cached", "--others", "--exclude-standard"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("not a git repository (or git is unavailable)")
    names = proc.stdout.decode("utf-8", "replace").split("\0")
    files = []
    for name in names:
        if not name:
            continue
        if any(fnmatch.fnmatch(name, pat) for pat in extra_excludes):
            continue
        if Path(name).suffix.lower() in BINARY_EXTENSIONS:
            continue
        if (root / name).is_file():
            files.append(name)
    return sorted(files)


def scan(root: Path, tags: list[str], ignore_case: bool = False,
         excludes: list[str] | None = None) -> list[Marker]:
    """Every marker occurrence in the tracked files under *root*."""
    pattern = build_pattern(tags, ignore_case)
    markers: list[Marker] = []
    for rel in tracked_files(root, excludes or []):
        try:
            data = (root / rel).read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue  # sniffed as binary
        text = data.decode("utf-8", "replace")
        for i, line in enumerate(text.splitlines(), 1):
            m = pattern.search(line)
            if not m:
                continue
            rest = line[m.end():].strip(" -:").strip()
            tag = m.group(0).rstrip(":").upper()
            markers.append(Marker(rel, i, tag, rest[:160]))
    return markers
