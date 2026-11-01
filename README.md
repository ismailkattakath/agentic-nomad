# agentic-nomad

A Claude Code project that plans cheap trips and handles the booking lifecycle — search, book,
pay, change, cancel, refund, support — with **a human approval on every spend**.

## Quick start

```bash
gh repo clone ismailkattakath/agentic-nomad && cd agentic-nomad
direnv allow                 # or: nix develop
nix run .#env-doctor         # which keys are set (names only)
claude                       # approve the project MCP servers when prompted
```

Then ask: *"Cheapest way from <home> to <destination>, <dates>, one adult, hostel or budget hotel."*

**Search works with no keys** (fli, Kiwi, Trivago, Airbnb). Apify needs the user-scope `apify`
plugin. LiteAPI rates (and its optional sandbox booking rail) need a free **LiteAPI sandbox** key
(`LITEAPI_API_KEY`); until it is set, Claude Code warns at startup and the `liteapi` server fails
to authenticate — expected. Bookings themselves are made on the supplier's own site
(`book-trip` skill), which needs no key.

## What's inside

| Piece | Path |
|---|---|
| Project memory (start here) | `CLAUDE.md` |
| Why this stack, what it beat | `docs/adr/0001-stack.md` |
| MCP servers (pinned) | `.mcp.json` |
| Redaction + host-policy hooks, tests | `.claude/hooks/` |
| Skills | `.claude/skills/` — one directory per skill |
| Subagents | `.claude/agents/` — one file per agent |
| Policy | `.claude/rules/` |
| Operating model (who does what) | `docs/adr/0002-operating-model.md` |

## Secrets

Keys reach MCP servers only through `${VAR}` expansion in `.mcp.json`. Supply them from
`.envrc.local` (computed from the Keychain) or by launching under a wrapper such as
`secret exec LITEAPI_API_KEY=<keychain handle> -- claude`. Nothing secret is committed.

Stripe connects over **OAuth**, not a key — why: `docs/adr/0001-stack.md` § Money.

## Host allowlist

Where the browser may fill a passport field, and whose emails count as sign-in codes, is **your**
data, so it is not in the repo. Copy the shape and put your own domains in it:

```bash
mkdir -p ~/.config/agentic-nomad
cp .claude/hooks/hosts.example.json ~/.config/agentic-nomad/hosts.json   # then edit
```

Another path: set `AGENTIC_NOMAD_HOSTS`. If the file is missing or malformed,
`hostpolicy.py` (and so `fill-secret.mjs`) **refuses every fill**. It never falls back to allow.
