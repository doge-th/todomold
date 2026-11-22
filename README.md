# todomold 🍄

[![CI](https://img.shields.io/github/actions/workflow/status/doge-th/todomold/ci.yml?branch=main&label=CI)](https://github.com/doge-th/todomold/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

**Every TODO in your repo, with who wrote it and how long it's been rotting.**

`grep -rn TODO` finds markers; todomold interrogates git blame and ranks them
by age — the oldest, moldiest TODOs first, then who owes the most. Zero
dependencies, one command.

```
$ todomold psf/requests

todomold v0.1.0  ·  /tmp/ghs-demo/requests  ·  12 markers · 12 blamed

The mold ranking (oldest first) — top 8
   14.3y  ████░░░░░░░░░░  src/requests/auth.py:213  [XXX] not implemented yet  (Peter Montagner, 2012-08)
   14.3y  ████░░░░░░░░░░  src/requests/auth.py:247  [XXX] handle auth-int.  (Peter Montagner, 2012-08)
   14.3y  ████░░░░░░░░░░  src/requests/auth.py:252  [XXX] should the partial digests be encoded too?  (Peter Montagner, 2012-08)
   13.9y  ████░░░░░░░░░░  src/requests/hooks.py:29  [TODO] response is the only one  (Kenneth Reitz, 2012-12)
   11.1y  ███░░░░░░░░░░░  src/requests/adapters.py:715  [TODO] Remove this in 3.0.0: see #2811  (Cory Benfield, 2015-10)
   10.5y  ███░░░░░░░░░░░  tests/test_utils.py:559  [XXX] unsure whether this is reasonable behavior  (Brett Higgins, 2016-05)
    9.5y  ███░░░░░░░░░░░  tests/test_testserver.py:97  [TODO] figure out why this sometimes fails when using pytest-xdist.  (Kenneth Reitz, 2017-05)
    5.0y  █░░░░░░░░░░░░░  tests/test_requests.py:654  [XXX] "  (Nate Prewitt, 2021-11)

Who owes the most
  Nate Prewitt        5  ██████░░░░░░░░  42%
  Peter Montagner     3  ████░░░░░░░░░░  25%
  Kenneth Reitz       2  ██░░░░░░░░░░░░  17%
  Cory Benfield       1  █░░░░░░░░░░░░░  8%
  Brett Higgins       1  █░░░░░░░░░░░░░  8%

By tag
  TODO        7  ████████░░░░░░
  XXX         5  ██████░░░░░░░░
```

*(real output — a locally cloned [psf/requests](https://github.com/psf/requests).
A 2012 XXX still marked "not implemented yet", and a "Remove this in 3.0.0"
that has survived every release since 3.0.0. This is what mold looks like.)*

## What you get

- **The mold ranking** — every marker, oldest first, with author and date.
  Great for a retro: "these ten lines predate the framework upgrade."
- **Who owes the most** — marker count per author. Meant kindly; mostly it
  tells you who did the most archaeology-prevention work.
- **By tag** — TODO vs FIXME vs HACK vs XXX at a glance.
- Uncommitted lines show as `Not Committed Yet` — your own fresh guilt included.

## Install

```bash
pip install git+https://github.com/doge-th/todomold.git
# or without touching your environment:
pipx install git+https://github.com/doge-th/todomold.git
uvx --from git+https://github.com/doge-th/todomold.git todomold .
```

## Usage

```bash
todomold .                        # whole repo, default tags TODO FIXME HACK XXX
todomold src/                     # just a subtree
todomold . --tag FIXME --tag HACK # hunt only what scares you
todomold . --ignore-case          # also match lowercase todo/...
todomold . --top 25               # longer rankings
todomold . --exclude "tests/**"   # skip a glob (repeatable)
todomold . --no-blame             # fast scan, no author/age (big repos)
todomold . --json                 # machine-readable, every entry
todomold . --markdown             # paste-ready table for issues/retros
```

`--json` includes every entry with path, line, tag, text, author, date and
computed `age_days`, sorted oldest first:

```bash
todomold . --json | jq -r '.entries[:5][] | [.age_days, .path, .line] | @tsv'
```

## Method (and its honest limits)

- Markers are matched with word boundaries against your tag list
  (`TODO FIXME HACK XXX` by default), case-sensitive unless `--ignore-case`.
  Lowercase "todo list" in a README will not match without the flag.
- Author and date come from `git blame --porcelain` on the current worktree,
  so ages reflect *when that line was last written*, not when the TODO was
  "created" — a reflow moves the timestamp. That's the honest price of
  line-level archaeology.
- Blame runs once per file that contains matches. On very large repos, use
  `--no-blame` for a fast count-only pass.
- Honors [`NO_COLOR`](https://no-color.org/); plain output when piped.

## 中文说明

**todomold:把仓库里所有 TODO/FIXME/HACK 翻出来,用 git blame 标上作者和
年龄,按腐烂程度排序。** `grep TODO` 只能找到,不能审判——谁写的、放了
多久、哪些是三年前就该删的,一条命令全部现形。零依赖,离线可用。

```bash
pip install git+https://github.com/doge-th/todomold.git
todomold .                       # 霉变排行 + 每人欠的账 + 标签分布
todomold . --tag FIXME           # 只盯最吓人的
todomold . --no-blame            # 大仓库快速模式
```

年龄 = 当前这行代码最后被写下的时间(行级考古的诚实代价:重排版会刷新
时间戳)。配套工具:[toktree](https://github.com/doge-th/toktree)(上下文
窗口预算)和 [githotspot](https://github.com/doge-th/githotspot)(churn ×
复杂度热点)——三个一起看,你的仓库就没有秘密了。

## Development

```bash
python -m unittest discover -s tests   # zero-dep suite, incl. real git blame tests
```

## License

[MIT](LICENSE) © 2026 doge-th
