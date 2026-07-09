# `tools` ↔ `permission` — the lossy translation

Claude Code scopes a subagent with a flat **allowlist** (`tools:`). OpenCode
scopes an agent with a **permission map** (`permission:`) that is per-tool
*and* per-command (glob patterns on `bash`). The two models do not line up
1:1; this file documents the asymmetry and the deterministic rules we apply.
Grounded in `doc/subagent-authoring-compare.md` §3–4.

## The asymmetry

| Aspect            | Claude `tools:`                          | OpenCode `permission:`                          |
| ----------------- | ---------------------------------------- | ----------------------------------------------- |
| Shape             | comma list or YAML list of tool names    | map: `read`/`edit`/`bash`/`webfetch` → verb     |
| Verbs             | implicit "allow" (listed = allowed)      | `allow` / `ask` / `deny`                        |
| Command grain     | tool-level only                          | per-command via glob (`bash: {"git push": ask}`)|
| Omission default  | absent → inherit ALL main-agent tools    | absent → platform default rule                  |

There is no way to express "may run `git diff` but not `git push`" in
Claude's `tools:`. Command-level granularity is **lost** going OC → Claude.

## Claude → OpenCode (widen list into map)

Map each listed Claude tool to a permission key set to `allow`; set every
capability the list does **not** grant to `deny` (least privilege — the
author named exactly what they needed).

Tool → permission-key mapping:

| Claude tool(s)                         | OpenCode key | Verb if present | Verb if absent |
| -------------------------------------- | ------------ | --------------- | -------------- |
| `Read`, `Grep`, `Glob`, `LS`           | `read`       | `allow`         | `allow`*       |
| `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | `edit` | `allow`         | `deny`         |
| `Bash`                                 | `bash`       | `allow`         | `deny`         |
| `WebFetch`, `WebSearch`                | `webfetch`   | `allow`         | `deny`         |

\* `read` defaults to `allow` even when unlisted — a subagent that cannot
read files is rarely intended; note the assumption in the report rather than
locking it to `deny`.

Worked example — Claude `tools: Read, Grep, Glob` (read-only reviewer):

```yaml
permission:
  edit: deny
  bash: deny
  webfetch: deny
```

(Read is allowed by default, so it may be omitted or written `read: allow`.)
This reproduces the read-only reviewer in `doc/` exactly.

Notes to emit:

- `tools:` was absent in the source → the Claude subagent inherited **all**
  tools. Do not fabricate a restrictive map; emit `permission: { }` (empty =
  platform default) and note `source had no tools: — inherited all; review
  OpenCode defaults`.

## OpenCode → Claude (collapse map into list)

Walk the permission map; a key that is `allow` (or `ask`) contributes its
Claude tools to the allowlist; a key that is `deny` contributes nothing.

| OpenCode key = `allow`/`ask` | Claude tools added                 |
| ---------------------------- | ---------------------------------- |
| `read`                       | `Read, Grep, Glob`                 |
| `edit`                       | `Edit, Write`                      |
| `bash`                       | `Bash`                             |
| `webfetch`                   | `WebFetch, WebSearch`              |

Lossy points — **each gets a report line**:

- **`ask` verb**: Claude has no "ask per tool" — it is folded to *allowed*
  (the tool appears in `tools:`). Report: `permission '<key>: ask' → tool
  allowed in Claude (no per-tool prompt equivalent)`.
- **Per-command bash globs** (`bash: {"git push": ask, "*": allow}`):
  collapse to a single `Bash` entry. Report every glob rule dropped:
  `dropped bash command rule '<pattern>: <verb>' — Claude has no
  command-level scoping`.
- **All-deny map**: if every key is `deny`, the Claude equivalent is an
  empty-but-present `tools:` list. Emit `tools: []`? Claude reads that as
  "no tools." Prefer emitting a minimal `tools: Read, Grep, Glob` and note
  the reviewer-style intent — but only if the body clearly implies
  read-only. Otherwise report and ask.

Worked example — OpenCode reviewer:

```yaml
permission:
  edit: deny
  bash:
    "*": ask
    "git diff": allow
    "grep *": allow
  webfetch: deny
```

→ Claude:

```yaml
tools: Read, Grep, Glob, Bash
```

Report:

```
- bash had command-level rules ("*": ask, "git diff": allow, "grep *": allow)
  → collapsed to a single Bash grant; command scoping lost.
- webfetch: deny, edit: deny → WebFetch/WebSearch/Edit/Write omitted from tools.
```

## Guardrails

- Never emit a `permission` verb Claude can't honor and call it faithful —
  faithfulness lives in the **report**, not in a lossless-looking file.
- Do not validate tool names against a live registry; both platforms' tool
  inventories drift. Preserve unknown names in the report.
- When the collapse is genuinely ambiguous (all-deny, unusual glob mix),
  stop and ask rather than guessing a `tools:` line.
