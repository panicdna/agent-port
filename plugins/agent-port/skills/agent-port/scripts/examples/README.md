# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo maintains AI agent/subagent definitions from a single source of truth and
compiles them into platform-specific formats. There are currently two agents —
`code-reviewer` (read-only) and `test-runner` (edits + command-scoped bash) —
each targeting two platforms: **Claude Code** and **OpenCode**. The pair is
deliberate: `code-reviewer` is the lossless round-trip case, `test-runner` is the
lossy case (its OpenCode header carries `temperature`/`top_p`/`steps`/`color` and
per-command `bash` globs that Claude's frontmatter cannot express).

## Build

```bash
python build.py
```

`build.py` iterates the `AGENTS` registry (a dict keyed by agent name). For each
agent it reads `common/<agent>.prompt.md` (the shared prompt body) and writes two
outputs by prepending platform-specific YAML frontmatter:

- `claude/<agent>.md`   — Claude Code frontmatter (`tools:` allowlist, `model: sonnet`)
- `opencode/<agent>.md` — OpenCode frontmatter (`mode: subagent`, `permission:` map)

There is no test/lint setup; `build.py` has no dependencies beyond the standard library.

## Architecture

The core idea: **the prompt body lives in exactly one place, and platform differences
live only in frontmatter.**

- `common/*.prompt.md` — the canonical, platform-agnostic prompt. **Edit prompt content here.**
- `claude/*.md` and `opencode/*.md` — **generated artifacts**. Do not edit by hand; they are
  overwritten on the next `build.py` run. Any manual change here is lost.
- `build.py` — the compiler. The `AGENTS` dict holds, per agent, a `claude` and an
  `opencode` frontmatter header string; a single loop writes both artifacts. These
  headers define how the same intent is expressed per platform. Note the two
  platforms enforce access differently: Claude via a `tools:` allowlist,
  OpenCode via a `permission:` map (`edit`/`bash`/`webfetch` → `allow`/`ask`/`deny`,
  with per-command `bash` globs). That asymmetry is exactly what the `agent-convert`
  skill (repo root `SKILL.md`) translates and reports loss on.

## Adding or changing an agent

- To change what an agent *does*: edit the file in `common/`, then run `python build.py`.
- To add a new agent: create `common/<name>.prompt.md`, then add one entry to the `AGENTS`
  dict in `build.py` with a `claude` and an `opencode` header string. No other code changes —
  the loop picks it up. (The body must live in `common/`; a missing prompt file raises.)
- To support a new platform: add a third key (e.g. `"cursor"`) to each agent's header dict and
  a matching `mkdir` for its output directory. The write loop already iterates whatever keys
  are present per agent.
