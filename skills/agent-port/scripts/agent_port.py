#!/usr/bin/env python3
"""agent-port — Claude Code <-> OpenCode subagent converter.

A deterministic, stdlib-only implementation of the CLI designed in
doc/CLI 구성안.md. It is the executable sibling of the `agent-convert` skill
(SKILL.md): same mapping rules (references/field-mapping.md,
references/permission-model.md), but scriptable with CI-friendly exit codes.

Subcommands:
    convert <file> [--from F] [--to T] [--out DIR] [--dry-run]
    check   <file> [--to T] [--strict]
    batch   <dir>  [--from F] [--to T] [--out DIR] [--dry-run] [--strict]

Exit codes (worst-of across files for batch):
    0  ok / lossy — converted; lossy conversions still succeed (loss is
                    reported, per the skill's "lossy is expected" principle)
    1  lossy under --strict — a field/rule was dropped and --strict was set,
                    so CI blocks; identical output, just a non-zero code
    2  error       — missing required field, ambiguous format, unmappable
                    model, or refused overwrite

Loss is always printed regardless of exit code. Use --strict in CI when any
data loss (e.g. temperature -> Claude) should fail the pipeline.
"""

import argparse
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Model alias tables (mirror references/field-mapping.md "Model alias table")
# --------------------------------------------------------------------------
ALIAS_TO_FULL = {
    "haiku": "anthropic/claude-haiku-4-5",
    "sonnet": "anthropic/claude-sonnet-4-5",
    "opus": "anthropic/claude-opus-4-1",
}
# Prefix -> alias for collapsing OpenCode ids back to Claude aliases.
FULL_PREFIX_TO_ALIAS = [
    ("anthropic/claude-haiku", "haiku"),
    ("anthropic/claude-sonnet", "sonnet"),
    ("anthropic/claude-opus", "opus"),
]

# OpenCode-only frontmatter keys that have no Claude equivalent (dropped OC->C).
OC_ONLY_SCALARS = ("temperature", "top_p", "steps", "hidden", "disable", "color")
# Provider-option keys we also drop with a warning if present.
OC_PROVIDER_OPTS = ("reasoningEffort", "providerOptions", "options")

# tools <-> permission mapping (references/permission-model.md)
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
READ_TOOLS = ("Read", "Grep", "Glob", "LS")
WEB_TOOLS = ("WebFetch", "WebSearch")


class ConvertError(Exception):
    """Hard failure for a single file (missing required field, ambiguity...)."""


# --------------------------------------------------------------------------
# Frontmatter parsing (a small, indentation-aware subset of YAML sufficient
# for both platforms' agent frontmatter: scalars, block/inline lists, and one
# level of nested maps for `permission`/`bash`).
# --------------------------------------------------------------------------
def split_frontmatter(text):
    """Return (frontmatter_text, body_text). Raises if no `---` fence pair."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ConvertError("no YAML frontmatter (missing opening '---')")
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            fm = "".join(lines[1:idx])
            body = "".join(lines[idx + 1:])
            return fm, body
    raise ConvertError("unterminated frontmatter (missing closing '---')")


def _leading(s):
    return len(s) - len(s.lstrip(" "))


def _scalar(v):
    v = v.strip()
    if v == "":
        return None
    if (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'"):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v) if "." not in v else float(v)
    except ValueError:
        return v


def _parse_list(lines, i, indent):
    items = []
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "":
            i += 1
            continue
        if _leading(ln) != indent or not ln.lstrip().startswith("- "):
            break
        items.append(_scalar(ln.lstrip()[2:]))
        i += 1
    return items, i


def _parse_block(lines, i):
    """Parse the block beginning at (or after blanks from) line i."""
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines):
        return None, i
    indent = _leading(lines[i])
    if lines[i].lstrip().startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines, i, indent):
    result = {}
    while i < len(lines):
        ln = lines[i]
        if ln.strip() == "" or ln.lstrip().startswith("#"):
            i += 1
            continue
        cur = _leading(ln)
        if cur < indent:
            break
        if cur > indent:  # stray deeper line; skip defensively
            i += 1
            continue
        key, _, val = ln.lstrip().partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip()
        i += 1
        if val == "":
            # peek: is there a deeper block belonging to this key?
            j = i
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and _leading(lines[j]) > indent:
                result[key], i = _parse_block(lines, i)
            else:
                result[key] = None
        else:
            result[key] = _scalar(val)
    return result, i


def parse_frontmatter(text):
    data, _ = _parse_map(text.splitlines(), 0, 0)
    return data


# --------------------------------------------------------------------------
# Format detection (references/field-mapping.md "Source-format detection")
# --------------------------------------------------------------------------
def detect_format(fm):
    """Return 'claude', 'opencode', or 'ambiguous'."""
    model = fm.get("model")
    oc_signals = (
        "mode" in fm
        or "permission" in fm
        or (isinstance(model, str) and "/" in model)
        or any(k in fm for k in OC_ONLY_SCALARS)
    )
    claude_signals = (
        "name" in fm
        or ("tools" in fm and "permission" not in fm)
        or (isinstance(model, str) and model in ALIAS_TO_FULL)
    )
    if oc_signals and claude_signals and ("name" in fm and "mode" in fm):
        return "ambiguous"
    if oc_signals:
        return "opencode"
    if claude_signals:
        return "claude"
    return "ambiguous"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def normalize_tools(raw):
    """tools may be a YAML list or a comma string; return a list[str]."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def collapse_model(model):
    """OpenCode full id -> (alias|None, warning|None)."""
    for prefix, alias in FULL_PREFIX_TO_ALIAS:
        if model.startswith(prefix):
            return alias, None
    return None, (
        f"non-Anthropic model '{model}' has no Claude equivalent; "
        "set model manually"
    )


def _norm_name(stem):
    return "-".join(stem.lower().split())


# --------------------------------------------------------------------------
# Claude -> OpenCode  (mostly additive)
# --------------------------------------------------------------------------
def claude_to_opencode(fm, stem):
    warnings = []
    if "description" not in fm or not fm.get("description"):
        raise ConvertError("Claude source missing required 'description'")

    name = fm.get("name") or stem
    out_name = _norm_name(str(name))
    if out_name != stem:
        warnings.append(
            f"renamed: OpenCode file must be '{out_name}.md' "
            f"(name '{name}' != source filename '{stem}')"
        )

    lines = ["---", f"description: {fm['description']}", "mode: subagent"]

    model = fm.get("model")
    if isinstance(model, str) and model in ALIAS_TO_FULL:
        full = ALIAS_TO_FULL[model]
        lines.append(f"model: {full}")
        warnings.append(f"model expanded to {full} — verify with 'opencode models'")
    elif isinstance(model, str) and "/" in model:
        lines.append(f"model: {model}")  # already a full id
    elif model:
        warnings.append(f"unknown model alias '{model}' — left as-is")
        lines.append(f"model: {model}")

    tools = normalize_tools(fm.get("tools"))
    lines.append("")
    if tools is None:
        lines.append("permission: {}")
        warnings.append(
            "source had no tools: — Claude inherited ALL tools; emitted empty "
            "permission map (platform default). Review OpenCode defaults."
        )
    else:
        has_edit = any(t in tools for t in EDIT_TOOLS)
        has_bash = "Bash" in tools
        has_web = any(t in tools for t in WEB_TOOLS)
        lines.append("permission:")
        lines.append(f"  edit: {'allow' if has_edit else 'deny'}")
        lines.append(f"  bash: {'allow' if has_bash else 'deny'}")
        lines.append(f"  webfetch: {'allow' if has_web else 'deny'}")
        # read is allow-by-default in OpenCode, so it is intentionally omitted.
    lines.append("---")
    return "\n".join(lines) + "\n", out_name, warnings


# --------------------------------------------------------------------------
# OpenCode -> Claude  (lossy)
# --------------------------------------------------------------------------
def opencode_to_claude(fm, stem, line_of):
    warnings = []
    if "description" not in fm or not fm.get("description"):
        raise ConvertError("OpenCode source missing required 'description'")

    name = _norm_name(stem)
    if name != stem:
        warnings.append(f"derived name '{name}' from filename '{stem}' (normalized)")

    lines = ["---", f"name: {name}", f"description: {fm['description']}"]

    # mode
    mode = fm.get("mode")
    if mode in ("primary", "all"):
        warnings.append(
            f"{line_of('mode')}mode: {mode} → dropped; Claude has no primary/all "
            "concept (subagents only)"
        )

    # permission -> tools
    perm = fm.get("permission") or {}
    tools = []

    def granted(key):
        v = perm.get(key)
        if isinstance(v, dict):  # e.g. bash: {"*": ask, ...}
            return any(str(x) in ("allow", "ask") for x in v.values())
        if v is None:
            return None  # unspecified
        return str(v) in ("allow", "ask")

    # read: default allow when unspecified
    r = granted("read")
    if r is None or r:
        tools += list(READ_TOOLS[:3])  # Read, Grep, Glob
    if granted("edit"):
        tools += ["Edit", "Write"]
    if granted("bash"):
        tools += ["Bash"]
        b = perm.get("bash")
        if isinstance(b, dict):
            rules = ", ".join(f'"{k}": {v}' for k, v in b.items())
            warnings.append(
                f"{line_of('permission')}bash had command-level rules ({rules}) "
                "→ collapsed to a single Bash grant; command scoping LOST"
            )
    if granted("webfetch"):
        tools += list(WEB_TOOLS)

    # report 'ask' verbs folded to allow
    for key in ("read", "edit", "bash", "webfetch"):
        v = perm.get(key)
        if v == "ask":
            warnings.append(
                f"permission '{key}: ask' → tool allowed in Claude "
                "(no per-tool prompt equivalent)"
            )

    if not tools:
        raise ConvertError(
            "all-deny permission map → ambiguous in Claude ('tools: []' means "
            "no tools). Set tools manually or confirm intent."
        )
    lines.append("tools:")
    for t in tools:
        lines.append(f"  - {t}")

    # model
    model = fm.get("model")
    if isinstance(model, str) and "/" in model:
        alias, warn = collapse_model(model)
        if alias:
            lines.append(f"model: {alias}")
            warnings.append(
                f"{line_of('model')}model '{model}' → alias '{alias}' — "
                "verify with 'opencode models'"
            )
        else:
            warnings.append(f"{line_of('model')}{warn}")  # drop model line
    elif model:
        lines.append(f"model: {model}")

    # dropped OpenCode-only fields
    for k in OC_ONLY_SCALARS + OC_PROVIDER_OPTS:
        if k in fm:
            note = {
                "steps": "iteration cap belongs to CLI maxTurns, not frontmatter",
            }.get(k, "Claude frontmatter has no equivalent")
            warnings.append(f"{line_of(k)}dropped '{k}: {fm[k]}' — {note}")

    lines.append("---")
    return "\n".join(lines) + "\n", name, warnings


# --------------------------------------------------------------------------
# Orchestration for one file
# --------------------------------------------------------------------------
def _line_indexer(fm_text):
    """Return a fn key -> 'path:line ' prefix for warnings (best-effort)."""
    idx = {}
    for n, ln in enumerate(fm_text.splitlines(), start=2):  # +1 for '---', 1-based
        key = ln.lstrip().partition(":")[0].strip().strip('"').strip("'")
        if key and key not in idx and _leading(ln) == 0:
            idx[key] = n

    def prefix(key):
        return f"L{idx[key]}: " if key in idx else ""

    return prefix


def convert_file(path, to=None, frm=None):
    """Convert one file. Return dict with keys:
    source, target, status ('ok'|'lossy'|'skipped'), out_name, out_text, warnings.
    Raises ConvertError on hard failure."""
    text = path.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(text)
    fm = parse_frontmatter(fm_text)

    source = frm or detect_format(fm)
    if source == "ambiguous":
        raise ConvertError(
            "ambiguous source format (both Claude and OpenCode signals); "
            "pass --from to disambiguate"
        )
    target = to or ("claude" if source == "opencode" else "opencode")
    if target == source:
        return {
            "source": source, "target": target, "status": "skipped",
            "out_name": path.stem, "out_text": None, "warnings": [],
        }

    line_of = _line_indexer(fm_text)
    if source == "claude":
        new_fm, out_name, warnings = claude_to_opencode(fm, path.stem)
    else:
        new_fm, out_name, warnings = opencode_to_claude(fm, path.stem, line_of)

    # body already carries the newline(s) that followed the source's closing
    # '---'; new_fm ends with the target's closing '---\n'. Concatenate as-is
    # to preserve the body verbatim (adding a separator would double the gap).
    out_text = new_fm + body
    # Only genuine information loss marks 'lossy'. Advisory notes (model-id
    # verify, filename normalization) do not — they keep status 'ok'.
    loss_markers = ("dropped", "LOST", "no Claude equivalent", "no per-tool prompt")
    lossy = source == "opencode" and any(
        any(m in w for m in loss_markers) for w in warnings
    )
    status = "lossy" if lossy else "ok"
    return {
        "source": source, "target": target, "status": status,
        "out_name": out_name, "out_text": out_text, "warnings": warnings,
    }


def default_out_dir(target):
    return Path(".opencode/agents") if target == "opencode" else Path(".claude/agents")


# --------------------------------------------------------------------------
# Subcommand handlers
# --------------------------------------------------------------------------
def _print_result(path, res):
    arrow = f"{res['source']}→{res['target']}"
    print(f"{path.name}: {arrow} [{res['status']}]")
    for w in res["warnings"]:
        print(f"  - {w}")


def cmd_convert(args):
    path = Path(args.path)
    try:
        res = convert_file(path, to=args.to, frm=getattr(args, "from"))
    except ConvertError as e:
        print(f"{path.name}: ERROR — {e}", file=sys.stderr)
        return 2
    _print_result(path, res)
    if res["status"] == "skipped":
        return 0
    out_dir = Path(args.out) if args.out else default_out_dir(res["target"])
    out_path = out_dir / f"{res['out_name']}.md"
    if args.dry_run:
        print(f"  (dry-run) would write {out_path}")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and out_path.read_text(encoding="utf-8") != res["out_text"]:
            print(f"  refusing to overwrite differing {out_path} "
                  "(remove it or pick --out); skipped write", file=sys.stderr)
            return 2
        out_path.write_text(res["out_text"], encoding="utf-8")
        print(f"  wrote {out_path}")
    return 1 if (res["status"] == "lossy" and args.strict) else 0


def cmd_check(args):
    path = Path(args.path)
    try:
        res = convert_file(path, to=args.to)
    except ConvertError as e:
        print(f"{path.name}: ERROR — {e}", file=sys.stderr)
        return 2
    _print_result(path, res)
    if res["status"] == "lossy" and args.strict:
        return 1
    return 0


def cmd_batch(args):
    root = Path(args.path)
    if not root.is_dir():
        print(f"{root}: not a directory", file=sys.stderr)
        return 2
    files = sorted(p for p in root.glob("*.md") if p.name.lower() != "readme.md")
    if not files:
        print(f"{root}: no *.md agent files found")
        return 0
    worst = 0
    for path in files:
        try:
            res = convert_file(path, to=args.to, frm=getattr(args, "from"))
        except ConvertError as e:
            print(f"{path.name}: ERROR — {e}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        _print_result(path, res)
        if res["status"] == "skipped":
            continue
        out_dir = Path(args.out) if args.out else default_out_dir(res["target"])
        out_path = out_dir / f"{res['out_name']}.md"
        if args.dry_run:
            print(f"  (dry-run) would write {out_path}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(res["out_text"], encoding="utf-8")
            print(f"  wrote {out_path}")
        if res["status"] == "lossy" and args.strict:
            worst = max(worst, 1)
    return worst


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="agent-port",
        description="Convert subagent definitions between Claude Code and OpenCode.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_dir_flags(sp):
        sp.add_argument("--from", choices=["opencode", "claude"], default=None,
                        help="source format (auto-detected from frontmatter if omitted)")
        sp.add_argument("--to", choices=["opencode", "claude"], default=None,
                        help="target format (defaults to the opposite of source)")
        sp.add_argument("--out", default=None, help="output directory")
        sp.add_argument("--dry-run", action="store_true",
                        help="resolve output paths and report, but write nothing")
        sp.add_argument("--strict", action="store_true",
                        help="exit 1 (non-zero) when the conversion is lossy")

    c = sub.add_parser("convert", help="convert a single agent file")
    c.add_argument("path")
    add_dir_flags(c)
    c.set_defaults(func=cmd_convert)

    ck = sub.add_parser("check", help="validate + report loss, write nothing")
    ck.add_argument("path")
    ck.add_argument("--to", choices=["opencode", "claude"], default=None)
    ck.add_argument("--strict", action="store_true",
                    help="treat any loss as a non-zero (blocking) result")
    ck.set_defaults(func=cmd_check)

    b = sub.add_parser("batch", help="convert every *.md agent in a directory")
    b.add_argument("path")
    add_dir_flags(b)
    b.set_defaults(func=cmd_batch)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
