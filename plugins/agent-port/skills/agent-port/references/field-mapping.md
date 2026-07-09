# Field mapping — Claude Code subagent ↔ OpenCode agent

Single source of truth for field-by-field transformation, both directions.
`SKILL.md` links here from Step 3; do not duplicate this table in the main
file. Grounded in `doc/subagent-authoring-compare.md`.

## Direction is symmetric in intent, asymmetric in loss

- **Claude → OpenCode** is mostly *additive* (add `mode`, expand model id,
  widen `tools` into a `permission` map). Little is lost.
- **OpenCode → Claude** is *lossy*: OpenCode has fields Claude's frontmatter
  cannot express (`temperature`, `top_p`, `steps`, per-command `bash`
  patterns, `disable`/`hidden`/`color`, provider options like
  `reasoningEffort`). Never drop these silently — report each one.

## Source-format detection (frontmatter sniff)

Read the frontmatter and classify before converting. Do **not** rely on the
file path alone.

| Signal present                                              | Source is  |
| ----------------------------------------------------------- | ---------- |
| `mode:` key (`subagent`/`primary`/`all`)                    | OpenCode   |
| `permission:` map                                           | OpenCode   |
| `model:` value contains a `/` (e.g. `anthropic/claude-...`) | OpenCode   |
| `temperature`, `top_p`, `steps`, `hidden`, `disable`        | OpenCode   |
| top-level `name:` **and** no OpenCode signals               | Claude     |
| `tools:` (comma list or YAML list) and no `permission:`     | Claude     |
| `model:` is a bare alias (`sonnet`/`opus`/`haiku`)          | Claude     |

If signals conflict (e.g. both `name:` and `mode:`), report ambiguity and
ask the user which source format to assume. Do not guess.

`--to` defaults to the **opposite** of the detected source. If the user
passes `--to` equal to the detected source, it is a no-op — report and skip.

## Frontmatter field map

| Purpose                | Claude Code                    | OpenCode                                  | Notes                                                          |
| ---------------------- | ------------------------------ | ----------------------------------------- | -------------------------------------------------------------- |
| Name                   | `name:` (required)             | filename stem (no `name:` key)            | See "Name ↔ filename" below.                                   |
| Description / delegation | `description:` (required)    | `description:` (required)                 | Pass through verbatim. Keep any "use proactively" triggers.    |
| Kind                   | subagent by folder location    | `mode: subagent`                          | C→OC: add `mode: subagent`. OC→C: drop `mode`, warn if `primary`/`all`. |
| Model                  | `model: sonnet`                | `model: anthropic/claude-sonnet-4-...`    | See model alias table. Always flag "verify with `opencode models`". |
| Tool access            | `tools: Read, Grep`            | `permission: { read: allow, edit: deny }` | See `permission-model.md` — the trickiest, lossy in OC→C.      |
| Creativity             | ✖ (unsupported)                | `temperature`, `top_p`                    | OC→C: drop + warn. C→OC: nothing to add.                       |
| Iteration cap          | CLI `maxTurns` only            | `steps`                                   | OC→C: drop + warn (belongs to CLI invocation, not frontmatter).|
| Visibility / misc      | ✖                              | `disable`, `hidden`, `color`              | OC→C: drop + warn.                                             |
| Provider options       | ✖                              | `reasoningEffort`, etc.                   | OC→C: drop + warn.                                             |
| System prompt          | body below `---`               | body below `---` (or `prompt: {file:…}`)  | Body transfers verbatim in both directions.                    |

Unknown top-level keys: drop with a warning. Neither platform accepts
arbitrary frontmatter keys.

## Name ↔ filename

OpenCode derives the agent name from the filename (`review.md` → `review`)
and has **no** `name:` field. Claude requires an explicit `name:`.

- **Claude → OpenCode**: remove the `name:` line; the output file MUST be
  named `<name>.md`. If the source file was `code-reviewer.md` but
  `name: reviewer`, the OpenCode output is `reviewer.md` — record the
  rename in the report.
- **OpenCode → Claude**: add `name: <filename-stem>`. Validate the stem
  against Claude's convention (lowercase, hyphens). If the stem has spaces
  or uppercase, normalize to lowercase-hyphen and report the derived name.

## Model alias table

Claude uses short aliases; OpenCode requires the full `provider/model-id`
path. IDs change over time — **always** append a report note telling the
user to confirm against `opencode models`.

| Claude alias | OpenCode (default full id)          | OC→C collapses from                        |
| ------------ | ----------------------------------- | ------------------------------------------ |
| `haiku`      | `anthropic/claude-haiku-4-5`        | `anthropic/claude-haiku-*`                 |
| `sonnet`     | `anthropic/claude-sonnet-4-5`       | `anthropic/claude-sonnet-*`                |
| `opus`       | `anthropic/claude-opus-4-1`         | `anthropic/claude-opus-*`                  |

Rules:

- **Claude → OpenCode**: expand the alias to the default full id above.
  Emit the note: `model expanded to <id> — verify with 'opencode models'`.
- **OpenCode → Claude**: collapse any `anthropic/claude-{opus,sonnet,haiku}-*`
  to its alias. If the OpenCode model is **non-Anthropic** (e.g.
  `openai/gpt-*`, `google/gemini-*`, `ollama/...`), Claude Code cannot run
  it — do **not** invent a mapping. Drop the `model:` line and report:
  `non-Anthropic model '<id>' has no Claude equivalent; set model manually`.
- If the alias/id is missing entirely, leave it absent (both platforms fall
  back to their default model) and note it.

## Migration checklist (mirrors doc §5, made bidirectional)

**Claude → OpenCode**

1. Delete the `name:` line; ensure output filename == the old `name`.
2. Add `mode: subagent`.
3. Expand `model:` alias → full `provider/model-id`.
4. Rewrite `tools:` → `permission:` (see `permission-model.md`).
5. Reuse the body verbatim.

**OpenCode → Claude**

1. Add `name:` from the filename stem.
2. Delete `mode:` (warn if it was `primary`/`all` — that concept is lost).
3. Collapse `model:` → alias (or drop + warn if non-Anthropic).
4. Rewrite `permission:` → `tools:` allowlist (lossy — see
   `permission-model.md`).
5. Drop `temperature`/`top_p`/`steps`/`hidden`/`disable`/`color`/provider
   options, **each with its own warning line**.
6. Reuse the body verbatim.
