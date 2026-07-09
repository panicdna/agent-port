---
description: Convert subagent/agent definitions between Claude Code and OpenCode (convert / check / batch) via the bundled agent_port CLI.
---

Invoke the `agent-port:agent-port` skill. Auto-detect the source format, drive the bundled `agent_port` CLI (`convert` a single file, `check` for validation-only with CI exit codes, or `batch` a whole agents directory), and report every lossy field (temperature, steps, per-command bash scoping, non-Anthropic models) instead of dropping it silently.

Arguments — e.g. `convert <path> --to {opencode|claude}`, `check <path>`, or `batch <dir> --to {opencode|claude}` (may be empty; ask for the file/direction if so): $ARGUMENTS
