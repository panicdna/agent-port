from pathlib import Path

ROOT = Path(__file__).parent

# One entry per agent. The prompt body is shared from common/<name>.prompt.md;
# only the per-platform frontmatter differs. To add an agent: drop a
# common/<name>.prompt.md and add an entry here — no other code changes.
AGENTS = {
    "code-reviewer": {
        "claude": """---
name: code-reviewer
description: Reviews source code for correctness, security, performance, and maintainability.
tools:
  - Read
  - Grep
  - Glob
model: sonnet
---

""",
        "opencode": """---
description: Reviews source code for correctness, security, performance, and maintainability.
mode: subagent
model: anthropic/claude-sonnet-4-5
temperature: 0.1

permission:
  edit: deny
  bash: deny
  webfetch: deny
---

""",
    },
    # Lossy-case demo: this agent edits files and runs *command-scoped* bash.
    # The OpenCode header carries fields Claude's frontmatter cannot express
    # (temperature, top_p, steps, color) and per-command bash globs. Converting
    # opencode/test-runner.md -> Claude must drop those and report each — see
    # the converter's loss report.
    "test-runner": {
        "claude": """---
name: test-runner
description: Runs the test suite, diagnoses failures, and applies minimal fixes.
tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Bash
model: sonnet
---

""",
        "opencode": """---
description: Runs the test suite, diagnoses failures, and applies minimal fixes.
mode: subagent
model: anthropic/claude-sonnet-4-5
temperature: 0.2
top_p: 0.9
steps: 40
color: green

permission:
  edit: allow
  webfetch: deny
  bash:
    "*": ask
    "pytest*": allow
    "python -m pytest*": allow
    "npm test*": allow
    "git diff*": allow
    "git push*": deny
    "rm -rf*": deny
---

""",
    },
}

(ROOT / "claude").mkdir(exist_ok=True)
(ROOT / "opencode").mkdir(exist_ok=True)

for name, headers in AGENTS.items():
    prompt = (ROOT / "common" / f"{name}.prompt.md").read_text(encoding="utf-8")
    for platform, header in headers.items():
        (ROOT / platform / f"{name}.md").write_text(header + prompt, encoding="utf-8")
        print(f"wrote {platform}/{name}.md")

print("Done.")
