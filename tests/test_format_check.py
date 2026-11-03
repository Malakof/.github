from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import format_check


OK = {"pass": True, "severity": "ok", "summary": "Format reviewed", "findings": []}
FAIL = {
    "pass": False, "severity": "fail", "summary": "Missing priority",
    "findings": [{"rule": "priority", "severity": "fail", "message": "Missing label"}],
}


def response(raw: bytes):
    return io.BytesIO(raw)


def envelope(verdict=OK):
    return json.dumps({"choices": [{"message": {"content": json.dumps(verdict)}}]}).encode()


class FormatCheckTransportTests(unittest.TestCase):
    def call(self, effects):
        with patch.object(format_check.urllib.request, "urlopen", side_effect=effects) as request:
            with patch("time.sleep"):
                verdict = format_check.call_llm("private-token", "system", "private-prompt", "test/model")
        return verdict, request.call_count

    def test_empty_response_is_unavailable_after_bounded_retries(self):
        verdict, count = self.call([response(b"") for _ in range(3)])
        self.assertEqual(count, 3)
        self.assertEqual(verdict["status"], "unavailable")
        self.assertIsNone(verdict["pass"])
        self.assertEqual(verdict["severity"], "warn")
        self.assertIn("empty", verdict["findings"][0]["message"].lower())

    def test_transient_invalid_response_recovers_without_changing_verdict(self):
        verdict, count = self.call([response(b"<html>private-prompt</html>"), response(envelope())])
        self.assertEqual(count, 2)
        self.assertEqual(verdict, OK)

    def test_invalid_payloads_never_become_a_successful_review(self):
        invalid = [
            b"<html>private-token private-prompt</html>", b"\xff", b"[]", b"{}",
            b'{"choices": []}', b'{"choices": [{"message": {"content": "oops"}}]}',
            envelope([]), envelope({**OK, "pass": "true"}),
            envelope({**OK, "summary": ""}), envelope({**OK, "severity": "unknown"}),
            envelope({**OK, "findings": ["private-prompt"]}),
            envelope({**OK, "findings": [{"rule": "x", "severity": "fail", "message": "x"}]}),
            envelope({**OK, "severity": "fail"}),
        ]
        for raw in invalid:
            with self.subTest(raw=raw):
                verdict, count = self.call([response(raw) for _ in range(3)])
                self.assertEqual(count, 3)
                self.assertEqual(verdict["status"], "unavailable")
                self.assertIsNone(verdict["pass"])
                diagnostic = json.dumps(verdict)
                self.assertNotIn("private-token", diagnostic)
                self.assertNotIn("private-prompt", diagnostic)

    def test_rate_limit_and_server_failure_are_retried(self):
        for status in (408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                error = urllib.error.HTTPError("https://example.invalid", status, "private-token", {}, io.BytesIO(b"private-prompt"))
                verdict, count = self.call([error, response(envelope())])
                self.assertEqual(verdict, OK)
                self.assertEqual(count, 2)

    def test_auth_failure_is_not_retried_or_disclosed(self):
        error = urllib.error.HTTPError("https://example.invalid", 401, "private-token", {}, io.BytesIO(b"private-prompt"))
        verdict, count = self.call([error])
        self.assertEqual(count, 1)
        self.assertEqual(verdict["status"], "unavailable")
        self.assertIn("401", verdict["findings"][0]["message"])
        self.assertNotIn("private", json.dumps(verdict))

    def test_network_and_timeout_failures_are_bounded_and_redacted(self):
        for error in (urllib.error.URLError("private-token"), TimeoutError("private-prompt")):
            with self.subTest(error=type(error).__name__):
                verdict, count = self.call([error] * 3)
                self.assertEqual(count, 3)
                self.assertEqual(verdict["status"], "unavailable")
                self.assertNotIn("private", json.dumps(verdict))

    def test_real_format_rejection_is_preserved_without_retry(self):
        verdict, count = self.call([response(envelope(FAIL))])
        self.assertEqual(verdict, FAIL)
        self.assertEqual(count, 1)

    def test_main_distinguishes_unavailable_from_validated_for_both_policies(self):
        for blocking, expected_exit in (("false", 0), ("true", 1)):
            with self.subTest(blocking=blocking):
                output = io.StringIO()
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(sys, "argv", ["format_check.py", "--repo", "owner/repo", "--issue", "1", "--blocking", blocking]))
                    stack.enter_context(patch.dict("os.environ", {"GH_MODELS_TOKEN": "private-token"}))
                    stack.enter_context(patch.object(format_check, "fetch_artifact", return_value={"title": "example"}))
                    stack.enter_context(patch.object(format_check, "load_governance", return_value={}))
                    stack.enter_context(patch.object(format_check, "build_prompts", return_value=("system", "private-prompt")))
                    stack.enter_context(patch.object(format_check.urllib.request, "urlopen", side_effect=[response(b"") for _ in range(3)]))
                    stack.enter_context(patch("time.sleep"))
                    comment = stack.enter_context(patch.object(format_check, "upsert_comment"))
                    stack.enter_context(contextlib.redirect_stdout(output))
                    self.assertEqual(format_check.main(), expected_exit)
                rendered = comment.call_args.args[3]
                self.assertIn("unavailable", rendered.lower())
                self.assertNotIn("Validated against", rendered)
                self.assertNotIn("Format check OK", output.getvalue())
                self.assertNotIn("private", rendered + output.getvalue())


class FormatCheckWorkflowTests(unittest.TestCase):
    def test_caller_checkout_precedes_pin_resolution_and_governance_checkout(self):
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.safe_load((root / ".github/workflows/format-check.yml").read_text())
        steps = workflow["jobs"]["check"]["steps"]
        self.assertEqual(steps[0]["uses"], "actions/checkout@v5")
        self.assertNotIn("repository", steps[0]["with"])
        pin_index = next(i for i, step in enumerate(steps) if step.get("id") == "pin")
        self.assertGreater(pin_index, 0)
        self.assertIn(".crystal-governance.yaml", steps[pin_index]["run"])
        governance = [(i, step) for i, step in enumerate(steps)
                      if step.get("with", {}).get("repository") == "Malakof/.github"]
        self.assertEqual(len(governance), 1)
        index, checkout = governance[0]
        self.assertGreater(index, pin_index)
        self.assertEqual(checkout["with"]["ref"], "${{ steps.pin.outputs.version }}")


if __name__ == "__main__":
    unittest.main()
