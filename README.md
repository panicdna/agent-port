# agent-port

A single-plugin [Claude Code](https://docs.claude.com/en/docs/claude-code) skills marketplace that hosts one tool: a skill which converts subagent/agent definition files between **Claude Code** and **[OpenCode](https://opencode.ai/docs/)**, in either direction, by driving a bundled deterministic CLI.

## Installation

Inside a Claude Code session:

```
/plugin marketplace add panicdna/agent-port
/plugin install agent-port
```

To update later:

```
/plugin update agent-port
```

To remove:

```
/plugin uninstall agent-port
```

## What it does

The skill is a thin, safe wrapper around a bundled Python CLI (`agent_port.py`,
stdlib-only). It translates the **frontmatter** between the two platforms and
copies the prompt body verbatim:

- **Format auto-detected** — reads the frontmatter to classify the source as
  Claude (`name:`/`tools:`, bare model alias) or OpenCode (`mode:`/`permission:`,
  full `provider/model-id`). `--to` defaults to the opposite; `--from` overrides.
- **Model aliases mapped** — `sonnet` ↔ `anthropic/claude-sonnet-4-5`,
  `opus` ↔ `anthropic/claude-opus-4-1`, `haiku` ↔ `anthropic/claude-haiku-4-5`.
  Non-Anthropic models (`openai/…`, `google/…`) have no Claude equivalent — the
  `model:` line is dropped and reported.
- **`tools:` ↔ `permission:`** — Claude's flat allowlist widens into OpenCode's
  `permission` map (Claude → OpenCode), and collapses back (OpenCode → Claude).
- **Loss reported, never silent** — OpenCode → Claude drops `temperature`,
  `top_p`, `steps`, `color`, per-command `bash` scoping, and non-Anthropic
  models. Each is printed as a warning line anchored to its source line
  (`L5: dropped 'temperature: 0.2' …`). Lossy is expected, not a failure.

The skill never mutates the source file.

## Quick usage

```
/agent-port convert <path> --to {opencode|claude} [--out <dir>] [--dry-run]
/agent-port check   <path>                        # validate only, write nothing
/agent-port batch   <dir>  --to {opencode|claude} [--out <dir>]
```

- **`convert`** — one file. Source auto-detected; `--to` defaults to the opposite.
- **`check`** — validate + print the loss report, write nothing (CI exit codes).
- **`batch`** — convert every `*.md` agent in a directory (`.claude/agents/` ↔
  `.opencode/agents/`).
- **`--dry-run`** — resolve output paths and report, but write nothing.
- **`--strict`** — make a lossy conversion exit non-zero (CI gating).

### Exit codes (CI)

| Code | Meaning |
| ---- | ------- |
| `0`  | converted OK — including **lossy** (loss is reported, not fatal) |
| `1`  | lossy **and** `--strict` set — same output, non-zero so CI can block |
| `2`  | error: missing required field, ambiguous format, unmappable model, refused overwrite |

## Conversion highlights

| Field           | Claude → OpenCode                          | OpenCode → Claude                                        |
| --------------- | ------------------------------------------ | -------------------------------------------------------- |
| Name            | drop `name:`, filename = `<name>.md`       | add `name:` from filename stem (normalized)              |
| Kind            | add `mode: subagent`                       | drop `mode` (warn if `primary`/`all`)                    |
| Model           | expand alias → full `provider/model-id`    | collapse `anthropic/claude-*` → alias; non-Anthropic dropped |
| Tool access     | `tools:` → `permission:` map               | `permission:` → `tools:` allowlist (**lossy**)           |
| Tuning          | —                                          | drop `temperature`/`top_p`/`steps`/`color` + warn        |
| Bash scoping    | —                                          | per-command globs collapse to a single `Bash` + warn     |
| Body            | verbatim                                   | verbatim                                                 |

Full field-by-field rules live in
[`field-mapping.md`](./plugins/agent-port/skills/agent-port/references/field-mapping.md);
the `tools:` ↔ `permission:` asymmetry (the lossy edge) is documented in
[`permission-model.md`](./plugins/agent-port/skills/agent-port/references/permission-model.md).

## The bundled CLI

The skill drives `plugins/agent-port/skills/agent-port/scripts/agent_port.py`
— a dependency-free Python 3 CLI you can also run directly:

```bash
cd plugins/agent-port/skills/agent-port/scripts
python3 agent_port.py check examples/opencode/test-runner.md      # lossy demo
python3 agent_port.py convert examples/claude/code-reviewer.md --to opencode --out /tmp/out
python3 -m unittest test_agent_port -v                            # 21 tests
```

Two demo agents in `scripts/examples/` (built from a single source by
`build.py`) double as test oracles: `code-reviewer` is the **lossless
round-trip** case (Claude → OpenCode → Claude reproduces the original exactly),
and `test-runner` is the **lossy** case that exercises every dropped-field and
collapsed-scoping warning.

## Repository structure

```
agent-port/
├── .claude-plugin/
│   └── marketplace.json                              # marketplace manifest
├── plugins/
│   └── agent-port/
│       ├── .claude-plugin/
│       │   └── plugin.json                           # plugin manifest
│       └── skills/
│           └── agent-port/
│               ├── SKILL.md                          # skill (drives the CLI)
│               ├── references/
│               │   ├── field-mapping.md              # field-by-field rules
│               │   └── permission-model.md           # tools ↔ permission
│               └── scripts/
│                   ├── agent_port.py                 # the CLI
│                   ├── test_agent_port.py            # 21 tests
│                   └── examples/                     # demo agents / fixtures
├── doc/                                              # design notes
├── README.md
└── LICENSE
```

## License

MIT — see [LICENSE](./LICENSE).
