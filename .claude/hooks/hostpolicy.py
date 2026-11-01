#!/usr/bin/env python3
"""Host policy: where each secret may be filled.

One source of truth, the operator's hosts.json, read here. .claude/tools/fill-secret.mjs shells
out to `python3 hostpolicy.py check <handle> <host>` rather than re-implementing the match.

The allowlist is the operator's data, so it lives OUTSIDE the repo:
  ${AGENTIC_NOMAD_HOSTS:-$HOME/.config/agentic-nomad/hosts.json}
Shape: .claude/hooks/hosts.example.json. A missing or malformed file refuses every fill
(fail closed) — an absent allowlist must never read as "allow".

Handle rules (handles follow the `secret` CLI convention <tool>:<host>:<kind>):
  travel:passport:<field>   -> any booking or document host
  anything else             -> refused
Portal logins are NOT handles: they live in Passwords.app and Apple's iCloud Passwords
extension fills them (operator, 2026-10-27) — one copy, matched to the saved site by Apple.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from urllib.parse import urlsplit


class PolicyUnavailable(Exception):
    """The allowlist could not be read; every caller must treat this as a refusal."""


def hosts_file() -> pathlib.Path:
    """Resolved on every call, so a test can point AGENTIC_NOMAD_HOSTS at a temp file."""
    env = os.environ.get("AGENTIC_NOMAD_HOSTS")
    if env:
        return pathlib.Path(env)
    return pathlib.Path.home() / ".config" / "agentic-nomad" / "hosts.json"


def load() -> dict:
    path = hosts_file()
    try:
        data = json.loads(path.read_text())
        policy = {
            "booking": tuple(data["booking_hosts"]),
            "document": tuple(data["document_hosts"]),
            "passport_prefix": data["passport_handle_prefix"],
        }
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise PolicyUnavailable(
            f"host allowlist unreadable at {path} ({type(e).__name__}); set "
            "AGENTIC_NOMAD_HOSTS or create it from .claude/hooks/hosts.example.json"
        ) from None
    lists_ok = all(
        isinstance(data[k], list) and all(isinstance(h, str) and h for h in data[k])
        for k in ("booking_hosts", "document_hosts")
    )
    prefix = policy["passport_prefix"]
    if not lists_ok or not isinstance(prefix, str) or not prefix:
        raise PolicyUnavailable(f"host allowlist at {path} has the wrong shape")
    return policy


def host_of(url: str) -> str:
    """The URL's host, or "" for anything a browser might parse differently.

    Python's urlsplit and the browser's WHATWG parser disagree on some inputs:
    `https://evil.example\\@airline.example/` is airline.example to Python but evil.example to
    Chromium (it reads `\\` as `/`). So reject backslashes, userinfo, whitespace and control
    characters, and anything that is not http(s), before matching.
    """
    if (
        not isinstance(url, str)
        or any(c in url for c in "\\@")
        or any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in url)
    ):
        return ""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            return ""
        return (parts.hostname or "").lower()
    except ValueError:
        return ""


def matches(host: str, allowed) -> bool:
    host = (host or "").lower().rstrip(".")
    return bool(host) and any(host == a or host.endswith("." + a) for a in allowed)


def free_host(host: str, policy: dict | None = None) -> bool:
    """A host where the browser may click and fill without a prompt."""
    p = policy or load()
    return matches(host, p["booking"] + p["document"])


def fill_allowed(handle: str, host: str, policy: dict | None = None) -> str | None:
    """None if `handle` may be filled on `host`, else the reason it may not."""
    p = policy or load()
    if handle.startswith(p["passport_prefix"]) and len(handle) > len(
        p["passport_prefix"]
    ):
        if free_host(host, p):
            return None
        return f"{host!r} is not a booking or document host in the allowlist"
    return f"handle {handle!r} is not travel:passport:<field>"


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] != "check":
        print("usage: hostpolicy.py check <handle> <host>", file=sys.stderr)
        return 2
    try:
        reason = fill_allowed(argv[2], argv[3])
    except PolicyUnavailable as e:
        reason = str(e)
    if reason:
        print(f"refused: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
