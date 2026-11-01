#!/usr/bin/env python3
"""PostToolUse redaction for the page-lab Chromium: secret values never reach Claude.

Every chrome-devtools result passes through here before Claude sees it (PostToolUse
updatedToolOutput, https://code.claude.com/docs/en/hooks). It masks:
  - field values whose label looks secret (passport, birth date, card, password, codes) or that
    fill-secret.mjs recorded in .claude/state/fills.json;
  - 4-8 digit runs in tab titles that talk about a code (a Gmail tab titled
    "<6 digits> is your PIN code" leaked a PIN into a page listing, 2026-10-27).
It never prompts and never blocks. Claude Code's own telemetry still captures the original.

History: until 2026-10-27 this module also tracked tab ownership and fed spend_guard.py, which
asked before browser actions. The operator removed that prompt gate (payment needs the card he
types at checkout, and no profile stores a card — rules/airline-logins.md); redaction stayed.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

SERVER = "plugin_page-lab_chrome-devtools"

FIELD_RE = re.compile(
    r'^(?P<head>\s*uid=\S+ (?:textbox|combobox|spinbutton|searchbox) "(?P<label>[^"\n]*)"'
    r'[^\n]*?\bvalue=")(?P<value>[^\n]*?)(?P<tail>"(?: |$))',
    re.M,
)
SENSITIVE_LABEL_RE = re.compile(
    r"passport|travel document|document number|birth|\bdob\b|expir|nationality|issu|"
    r"card ?number|cvv|cvc|security code|password|one-time|\botp\b|verification code|"
    r"^(?:dd|mm|yyyy|day|month|year)$",
    re.I,
)
LISTING_TITLE_RE = re.compile(
    r"^(?P<head>\d+: )(?P<title>.*)(?P<tail> \(\S+\)(?: \[selected\])?\s*)$", re.M
)
CODE_WORDS_RE = re.compile(
    r"code|pin\b|otp|passcode|verification|one-time|security", re.I
)
DIGITS_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")


def state_dir(env: dict) -> pathlib.Path:
    if env.get("NOMAD_STATE_DIR"):
        return pathlib.Path(env["NOMAD_STATE_DIR"])
    root = env.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return pathlib.Path(root) / ".claude" / "state"


def fill_labels(env: dict) -> set[str]:
    """Labels of fields fill-secret.mjs filled (state/fills.json); empty on any error."""
    try:
        data = json.loads((state_dir(env) / "fills.json").read_text())
        return {str(r["label"]).strip().lower() for r in data if r.get("label")}
    except Exception:
        return set()


def _redact_titles(text: str) -> str:
    def sub(m):
        title = m.group("title")
        if CODE_WORDS_RE.search(title):
            title = DIGITS_RE.sub("[code]", title)
        return m.group("head") + title + m.group("tail")

    return LISTING_TITLE_RE.sub(sub, text)


def _redact_text(text: str, labels: set[str]) -> str:
    text = _redact_titles(text)

    def sub(m):
        label = m.group("label").strip()
        if SENSITIVE_LABEL_RE.search(label) or label.lower() in labels:
            n = len(m.group("value"))
            return f"{m.group('head')}[redacted {n} chars]{m.group('tail')}"
        return m.group(0)

    return FIELD_RE.sub(sub, text)


def _rewrite(resp, fn):
    """Apply fn to every text string in an MCP response, keeping its shape."""
    if isinstance(resp, str):
        return fn(resp)
    if isinstance(resp, list):
        return [_rewrite(x, fn) for x in resp]
    if isinstance(resp, dict):
        out = dict(resp)
        if "content" in out:
            out["content"] = _rewrite(out["content"], fn)
        elif isinstance(out.get("text"), str):
            out["text"] = fn(out["text"])
        return out
    return resp


def redact(payload: dict, env: dict):
    """The response with secret-looking values masked, or None if nothing changed."""
    resp = payload.get("tool_response")
    labels = fill_labels(env)
    new = _rewrite(resp, lambda t: _redact_text(t, labels))
    return None if new == resp else new


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        print(f"page_scope: unreadable payload ({exc})", file=sys.stderr)
        return 0
    if not (isinstance(payload, dict) and isinstance(payload.get("tool_name"), str)):
        return 0
    try:
        new = redact(payload, dict(os.environ))
    except Exception as exc:  # cannot prove the output is clean: hide it
        print(f"page_scope: redaction failed ({exc})", file=sys.stderr)
        new = [
            {"type": "text", "text": "[page_scope: output hidden, redaction failed]"}
        ]
    if new is not None:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "updatedToolOutput": new,
                }
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
