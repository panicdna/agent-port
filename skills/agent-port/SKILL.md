---
name: agent-port
description: >-
  Convert subagent/agent definition files between Claude Code and OpenCode, in
  either direction, by driving the bundled `agent_port` CLI. Auto-detects the
  source format from frontmatter, maps name<->filename, model aliases
  (sonnet <-> anthropic/claude-...), and Claude's `tools` allowlist <-> OpenCode's
  `permission` map, preserving the prompt body verbatim. Reports lossy fields
  (temperature, steps, per-command bash permissions, non-Anthropic models)
  instead of dropping them silently. Three CLI subcommands: `convert` (single
  file), `check` (validate only, CI exit codes), and `batch` (a whole agents
  directory). Use when the user runs `/agent-port convert <path> --to
  {opencode|claude}`, or asks in Korean "claude agent 를 opencode 로 변환",
  "subagent 를 claude 로 바꿔줘", "이 에이전트 opencode 에서 쓰게 만들어",
  "agents 폴더 통째로 변환".
metadata:
  author: panicdna
  version: 1.0.0
  category: tooling
  tags: agent, subagent, opencode, claude-code, conversion, migration, cli
allowed-tools: Bash(python3 *) Read Glob
---

# agent-port — Claude Code ↔ OpenCode Subagent Converter (CLI-driven)

## Role

Drive the bundled, deterministic `agent_port` CLI to convert subagent
definition files between the two platforms **in either direction**, then relay
its report to the user. A Claude Code subagent lives at `.claude/agents/<name>.md`
with `name:`/`tools:` frontmatter; an OpenCode agent lives at
`.opencode/agents/<name>.md` with `mode:`/`permission:` frontmatter and no
`name:` key. The prompt body transfers verbatim; only the frontmatter is
translated.

You are a thin, safe wrapper: parse the user's arguments, run the CLI, interpret
its exit code, and present the conversion report. Do **not** re-implement the
mapping logic by hand — the CLI at `${CLAUDE_SKILL_DIR}/scripts/agent_port.py`
is the single deterministic source of behavior, grounded in
`references/field-mapping.md` and `references/permission-model.md`.

## Argument shape

Invoked as a slash command or via the Skill tool. Arguments pass through to the
CLI subcommand, parsed left to right:

```
/agent-port convert <path> [--from F] [--to T] [--out <dir>] [--dry-run] [--strict]
/agent-port check   <path> [--to T] [--strict]
/agent-port batch   <dir>  [--from F] [--to T] [--out <dir>] [--dry-run] [--strict]
```

- **subcommand** (`convert` | `check` | `batch`): if the user omits it, infer:
  a directory + "폴더 통째" / "batch" → `batch`; "검증"/"validate"/"check only"
  → `check`; otherwise `convert`.
- **`<path>`** (required): an agent `.md` file, or — for `batch` — an agents
  directory.
- **`--from {opencode|claude}`**: override source auto-detection.
- **`--to {opencode|claude}`**: target format; defaults to the opposite of the
  detected source.
- **`--out <dir>`**: destination directory. Defaults to `.opencode/agents/`
  (→ opencode) or `.claude/agents/` (→ claude).
- **`--dry-run`**: resolve output paths and print the plan + warnings, write
  nothing.
- **`--strict`**: make a lossy conversion exit non-zero (for CI gating).

## Step 1: Locate the CLI

The converter ships inside this skill bundle. Resolve it once:

```bash
SCRIPT="${CLAUDE_SKILL_DIR}/scripts/agent_port.py"
```

Do not copy it into the user's project. Run it in place.

## Step 2: Run the CLI

Pass the user's arguments straight through. Example — validate one OpenCode
agent without writing:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/agent_port.py" check path/to/agent.md
```

Convert a whole folder Claude → OpenCode:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/agent_port.py" batch .claude/agents --to opencode --out .opencode/agents
```

Prefer `--dry-run` first when the user has not confirmed writes, then re-run
without it once they approve. Never invent paths; if `--out` is unclear for a
write, run `--dry-run` and show where files *would* land.

## Step 3: Interpret the exit code

The CLI's exit code is the CI signal — relay it verbatim and act on it:

| Exit | Meaning | What you do |
| ---- | ------- | ----------- |
| `0`  | converted OK, including **lossy** (loss reported) | report success + any warnings |
| `1`  | lossy **and** `--strict` was set | report as a gated failure; list the loss |
| `2`  | error (missing field, ambiguous format, unmappable model, refused overwrite) | surface the stderr message; do not retry blindly |

Loss is **not** failure. A `lossy` status with a full warning list is a
successful conversion (OpenCode → Claude almost always drops something).

## Step 4: Present the report

Relay the CLI's own output faithfully — it already prints, per file:
`source→target [status]` and one `- warning` line each (dropped fields,
collapsed bash scoping, model-verify notes), anchored with `L<n>:` source
lines. Then add a short **Next steps** stanza:

- where files landed (or would, under `--dry-run`),
- what to hand-verify (`opencode models` for the expanded/collapsed model id),
- for OpenCode → Claude: that per-command `bash` scoping and tuning fields
  (`temperature`/`steps`/…) were dropped — re-apply via the CLI invocation if
  needed.

Keep it tight — do not restate every warning in prose; the CLI already listed
them.

## Failure modes & guardrails

- **Ambiguous source format** (both Claude and OpenCode signals): the CLI exits
  `2`; ask the user to pass `--from`.
- **`--to` equals detected source**: the CLI reports `skipped` and writes
  nothing — relay as a no-op.
- **Non-Anthropic model → Claude**: the CLI drops `model:` and warns; do not
  invent an alias.
- **Target exists and differs**: the CLI refuses to overwrite (exit `2`); offer
  `--out <other-dir>` or ask the user to remove the file.
- **Lossy is expected, not an error**: never treat a `lossy` status as a
  failure unless `--strict` was explicitly requested.
- **Missing `--out` on a write**: default dir is fine, but if the user seems to
  expect a specific location, run `--dry-run` first and confirm.
