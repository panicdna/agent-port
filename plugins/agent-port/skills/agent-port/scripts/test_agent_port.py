"""Tests for agent_port — run with:  python3 -m unittest test_agent_port -v

Proves the converter against the real demo fixtures in examples/ (the lossless
code-reviewer and the lossy test-runner) plus synthetic edge cases.
"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import agent_port as ap

REPO = Path(__file__).parent
CLAUDE = REPO / "examples" / "claude"
OPENCODE = REPO / "examples" / "opencode"


def write_tmp(text, name="agent.md"):
    d = Path(tempfile.mkdtemp())
    p = d / name
    p.write_text(text, encoding="utf-8")
    return p


class FrontmatterParser(unittest.TestCase):
    def test_nested_permission_and_bash_map(self):
        fm_text, _ = ap.split_frontmatter((OPENCODE / "test-runner.md").read_text())
        fm = ap.parse_frontmatter(fm_text)
        self.assertEqual(fm["mode"], "subagent")
        self.assertEqual(fm["temperature"], 0.2)
        self.assertEqual(fm["steps"], 40)
        self.assertIsInstance(fm["permission"], dict)
        self.assertEqual(fm["permission"]["edit"], "allow")
        # bash is a nested map of glob -> verb
        self.assertIsInstance(fm["permission"]["bash"], dict)
        self.assertEqual(fm["permission"]["bash"]["git push*"], "deny")
        self.assertEqual(fm["permission"]["bash"]["*"], "ask")

    def test_inline_and_block_tools(self):
        self.assertEqual(ap.normalize_tools("Read, Grep, Glob"), ["Read", "Grep", "Glob"])
        self.assertEqual(ap.normalize_tools(["Read", "Bash"]), ["Read", "Bash"])
        self.assertIsNone(ap.normalize_tools(None))

    def test_missing_fence_raises(self):
        with self.assertRaises(ap.ConvertError):
            ap.split_frontmatter("no frontmatter here\n")


class FormatDetection(unittest.TestCase):
    def test_detect_claude(self):
        fm_text, _ = ap.split_frontmatter((CLAUDE / "code-reviewer.md").read_text())
        self.assertEqual(ap.detect_format(ap.parse_frontmatter(fm_text)), "claude")

    def test_detect_opencode(self):
        fm_text, _ = ap.split_frontmatter((OPENCODE / "code-reviewer.md").read_text())
        self.assertEqual(ap.detect_format(ap.parse_frontmatter(fm_text)), "opencode")

    def test_ambiguous_when_name_and_mode(self):
        fm = {"name": "x", "mode": "subagent", "description": "d"}
        self.assertEqual(ap.detect_format(fm), "ambiguous")


class ModelMapping(unittest.TestCase):
    def test_collapse_anthropic(self):
        self.assertEqual(ap.collapse_model("anthropic/claude-sonnet-4-5"), ("sonnet", None))
        self.assertEqual(ap.collapse_model("anthropic/claude-opus-4-1"), ("opus", None))

    def test_non_anthropic_has_no_alias(self):
        alias, warn = ap.collapse_model("openai/gpt-4o")
        self.assertIsNone(alias)
        self.assertIn("no Claude equivalent", warn)


class RoundTrip(unittest.TestCase):
    def test_claude_oc_claude_is_identity(self):
        original = (CLAUDE / "code-reviewer.md").read_text()
        src = write_tmp(original, "code-reviewer.md")
        oc = ap.convert_file(src, to="opencode")
        self.assertEqual(oc["status"], "ok")
        # write the OC output, convert back
        oc_path = write_tmp(oc["out_text"], "code-reviewer.md")
        back = ap.convert_file(oc_path, to="claude")
        self.assertEqual(back["out_text"].rstrip("\n"), original.rstrip("\n"))

    def test_c2oc_permission_map(self):
        src = write_tmp((CLAUDE / "code-reviewer.md").read_text(), "code-reviewer.md")
        res = ap.convert_file(src, to="opencode")
        self.assertIn("mode: subagent", res["out_text"])
        self.assertIn("edit: deny", res["out_text"])
        self.assertIn("bash: deny", res["out_text"])
        self.assertIn("webfetch: deny", res["out_text"])
        self.assertIn("anthropic/claude-sonnet-4-5", res["out_text"])


class LossyConversion(unittest.TestCase):
    def setUp(self):
        src = write_tmp((OPENCODE / "test-runner.md").read_text(), "test-runner.md")
        self.res = ap.convert_file(src, to="claude")

    def test_status_lossy(self):
        self.assertEqual(self.res["status"], "lossy")

    def test_tools_collapsed(self):
        for t in ("Read", "Grep", "Glob", "Edit", "Write", "Bash"):
            self.assertIn(f"- {t}", self.res["out_text"])
        self.assertIn("model: sonnet", self.res["out_text"])

    def test_every_lossy_field_reported(self):
        blob = "\n".join(self.res["warnings"])
        self.assertIn("temperature", blob)
        self.assertIn("top_p", blob)
        self.assertIn("steps", blob)
        self.assertIn("color", blob)
        self.assertIn("command scoping LOST", blob)
        # the dangerous deny rules must be visible in the report
        self.assertIn("git push*", blob)
        self.assertIn("rm -rf*", blob)


class Guardrails(unittest.TestCase):
    def test_all_deny_raises(self):
        text = (
            "---\ndescription: d\nmode: subagent\n"
            "permission:\n  read: deny\n  edit: deny\n  bash: deny\n  webfetch: deny\n---\nbody\n"
        )
        with self.assertRaises(ap.ConvertError):
            ap.convert_file(write_tmp(text), to="claude")

    def test_missing_description_raises(self):
        text = "---\nname: x\ntools:\n  - Read\nmodel: sonnet\n---\nbody\n"
        with self.assertRaises(ap.ConvertError):
            ap.convert_file(write_tmp(text), to="opencode")

    def test_noop_when_target_equals_source(self):
        src = write_tmp((CLAUDE / "code-reviewer.md").read_text())
        res = ap.convert_file(src, to="claude")  # source is claude
        self.assertEqual(res["status"], "skipped")


class CliExitCodes(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ap.main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_check_lossy_is_zero_by_default(self):
        code, _ = self._run(["check", str(OPENCODE / "test-runner.md")])
        self.assertEqual(code, 0)

    def test_check_lossy_strict_is_one(self):
        code, _ = self._run(["check", str(OPENCODE / "test-runner.md"), "--strict"])
        self.assertEqual(code, 1)

    def test_check_lossless_is_zero(self):
        code, _ = self._run(["check", str(CLAUDE / "code-reviewer.md")])
        self.assertEqual(code, 0)

    def test_convert_writes_file(self):
        outdir = Path(tempfile.mkdtemp())
        code, txt = self._run(
            ["convert", str(CLAUDE / "code-reviewer.md"), "--to", "opencode", "--out", str(outdir)]
        )
        self.assertEqual(code, 0)
        self.assertTrue((outdir / "code-reviewer.md").exists())

    def test_batch_strict_nonzero(self):
        outdir = Path(tempfile.mkdtemp())
        code, _ = self._run(
            ["batch", str(OPENCODE), "--to", "claude", "--out", str(outdir), "--strict"]
        )
        self.assertEqual(code, 1)  # test-runner is lossy


if __name__ == "__main__":
    unittest.main(verbosity=2)
