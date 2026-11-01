"""Redaction, host policy and hook wiring. Stdlib unittest, offline."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS = pathlib.Path(__file__).resolve().parent.parent
ROOT = HOOKS.parent.parent
sys.path.insert(0, str(HOOKS))

import hostpolicy  # noqa: E402
import page_scope  # noqa: E402

B = "mcp__plugin_page-lab_chrome-devtools__"


def listing(*rows, selected=None):
    """A page-lab "## Pages" block, in the shape the real MCP returns (2026-10-26)."""
    lines = ["## Pages"]
    for pid, title, url in rows:
        lines.append(
            f"{pid}: {title} ({url})" + (" [selected]" if pid == selected else "")
        )
    return (
        "\n".join(lines)
        + "\n## Extension Service Workers\nsw-1: chrome-extension://x/sw.js\n"
    )


class Redaction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {"NOMAD_STATE_DIR": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def redacted(self, text):
        out = page_scope.redact({"tool_response": text}, self.env)
        return text if out is None else out

    def test_secret_fields_are_redacted(self):
        text = (
            'uid=7_37 textbox "Frequent flyer number or email" required value="a@b.c"\n'
            'uid=7_43 textbox "DD" required value="01"\n'
            'uid=7_49 textbox "YYYY" required value="2000"\n'
            'uid=7_50 textbox "day" required value="02"\n'
            'uid=8_1 textbox "Passport number" value="X0000000"\n'
            'uid=8_2 combobox "Nationality" value="Canada"\n'
            'uid=8_3 textbox "Date of birth" value="01/01/2000"\n'
        )
        out = self.redacted(text)
        for secret in ('01"', '02"', "2000", "X0000000", "Canada", "01/01/2000"):
            self.assertNotIn(secret, out, secret)
        self.assertIn('value="a@b.c"', out)  # not secret-looking, kept
        self.assertIn('value="[redacted 8 chars]"', out)

    def test_codes_in_tab_titles_are_redacted(self):
        text = listing(
            (
                10,
                "123456 is your PIN code - a@b.c - Gmail",
                "https://mail.google.com/x",
            ),
            (11, "Your OTP 9876 has arrived", "https://mail.google.com/y"),
            (12, "Flight AC 1234 to Paris", "https://www.airline.example/z"),
            selected=12,
        )
        out = self.redacted(text)
        self.assertNotIn("123456", out)
        self.assertNotIn("9876", out)
        self.assertIn("AC 1234", out)  # no code words: a flight number stays
        self.assertIn("10: [code] is your PIN code", out)
        self.assertIn(
            "(https://www.airline.example/z) [selected]", out
        )  # line shape kept

    def test_labels_recorded_by_the_filler_are_redacted(self):
        (pathlib.Path(self.tmp.name) / "fills.json").write_text(
            json.dumps([{"host": "x.com", "label": "Document ID"}])
        )
        out = self.redacted('uid=1_1 textbox "Document ID" value="ZZ999"\n')
        self.assertNotIn("ZZ999", out)

    def test_redaction_keeps_the_mcp_shape(self):
        resp = {
            "content": [{"type": "text", "text": 'uid=1 textbox "CVV" value="123"'}]
        }
        out = page_scope.redact({"tool_response": resp}, self.env)
        self.assertEqual(out["content"][0]["type"], "text")
        self.assertNotIn("123", out["content"][0]["text"])
        self.assertIsNone(page_scope.redact({"tool_response": "no fields"}, self.env))

    def test_hook_process_emits_updated_output_and_never_blocks(self):
        payload = {
            "tool_name": B + "take_snapshot",
            "tool_input": {"pageId": 7},
            "tool_response": [
                {"type": "text", "text": 'uid=1 textbox "Password" value="hunter2"'}
            ],
            "session_id": "s1",
        }
        r = subprocess.run(
            [sys.executable, str(HOOKS / "page_scope.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=self.env,
            check=True,
        )
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PostToolUse")
        self.assertNotIn("hunter2", json.dumps(out))
        g = subprocess.run(
            [sys.executable, str(HOOKS / "page_scope.py")],
            input="garbage",
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(g.returncode, 0)
        self.assertEqual(g.stdout, "")


class HostPolicy(unittest.TestCase):
    """Runs against hosts.example.json in a temp dir — never the operator's ~/.config."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hosts = pathlib.Path(self.tmp.name) / "hosts.json"
        shutil.copy(HOOKS / "hosts.example.json", self.hosts)
        self.saved = os.environ.get("AGENTIC_NOMAD_HOSTS")
        os.environ["AGENTIC_NOMAD_HOSTS"] = str(self.hosts)

    def tearDown(self):
        if self.saved is None:
            os.environ.pop("AGENTIC_NOMAD_HOSTS", None)
        else:
            os.environ["AGENTIC_NOMAD_HOSTS"] = self.saved
        self.tmp.cleanup()

    def test_passport_handles_fill_on_booking_and_document_hosts_only(self):
        for host in (
            "www.airline.example",
            "documents.example",
            "booking.other-airline.example",
        ):
            self.assertIsNone(
                hostpolicy.fill_allowed("travel:passport:number", host), host
            )
        for host in ("evil.example", "airline.example.evil.example", "", "travel"):
            self.assertIsNotNone(
                hostpolicy.fill_allowed("travel:passport:number", host), host
            )

    def test_host_of_rejects_parser_differentials(self):
        for url in (
            "https://evil.example\\@airline.example/",
            "https://user@airline.example@evil.example/",
            "https://evil.example\t.airline.example/",
            "javascript:alert(1)",
            "ftp://airline.example/",
        ):
            self.assertEqual(hostpolicy.host_of(url), "", url)
        self.assertEqual(
            hostpolicy.host_of("https://www.Airline.Example/x"), "www.airline.example"
        )

    def test_password_and_other_handles_are_refused(self):
        for h in (
            "loyalty:airline.example:password",  # logins come from Passwords.app
            "travel:passport:",
            "card:visa:number",
            "x",
        ):
            self.assertIsNotNone(hostpolicy.fill_allowed(h, "www.airline.example"), h)

    def run_cli(self, *a, hosts=None):
        env = dict(os.environ, AGENTIC_NOMAD_HOSTS=str(hosts or self.hosts))
        return subprocess.run(
            [sys.executable, str(HOOKS / "hostpolicy.py"), *a],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_cli_exit_codes(self):
        ok = ("check", "travel:passport:number", "www.airline.example")
        self.assertEqual(self.run_cli(*ok).returncode, 0)
        bad = ("check", "travel:passport:number", "evil.example")
        self.assertEqual(self.run_cli(*bad).returncode, 1)
        self.assertEqual(self.run_cli("bogus").returncode, 2)

    def test_missing_or_malformed_allowlist_fails_closed(self):
        ok = ("check", "travel:passport:number", "www.airline.example")
        missing = pathlib.Path(self.tmp.name) / "absent.json"
        r = self.run_cli(*ok, hosts=missing)
        self.assertEqual(r.returncode, 1)
        self.assertIn("allowlist unreadable", r.stderr)
        self.assertIn(str(missing), r.stderr)
        for broken in (
            "not json",
            "{}",
            '{"booking_hosts": "airline.example", "document_hosts": [],'
            ' "passport_handle_prefix": "travel:passport:"}',
            '{"booking_hosts": [], "document_hosts": [], "passport_handle_prefix": ""}',
        ):
            self.hosts.write_text(broken)
            self.assertEqual(self.run_cli(*ok).returncode, 1, broken)
            with self.assertRaises(hostpolicy.PolicyUnavailable):
                hostpolicy.fill_allowed("travel:passport:number", "www.airline.example")

    def test_real_allowlist_is_not_in_the_repo(self):
        # hostpolicy never reads a copy here; one would only be data waiting to be committed.
        self.assertFalse((HOOKS / "hosts.json").exists())


class Wiring(unittest.TestCase):
    def settings(self):
        return json.loads((ROOT / ".claude" / "settings.json").read_text())

    def test_post_hook_sees_every_page_lab_call(self):
        entries = [
            e
            for e in self.settings()["hooks"]["PostToolUse"]
            if any("page_scope.py" in h["command"] for h in e["hooks"])
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0]["matcher"], "^mcp__plugin_page-lab_chrome-devtools__.*"
        )

    def test_no_prompt_gate(self):
        # Operator decision 2026-10-27: no "Do you want to proceed?" from this repo.
        s = self.settings()
        self.assertNotIn("PreToolUse", s.get("hooks", {}))
        self.assertEqual(s["permissions"].get("ask", []), [])
        self.assertFalse((HOOKS / "spend_guard.py").exists())

    def test_every_mcp_json_server_is_enabled_or_disabled_explicitly(self):
        servers = set(json.loads((ROOT / ".mcp.json").read_text())["mcpServers"])
        s = self.settings()
        listed = set(s.get("enabledMcpjsonServers", [])) | set(
            s.get("disabledMcpjsonServers", [])
        )
        self.assertEqual(servers - listed, set())


if __name__ == "__main__":
    unittest.main()
