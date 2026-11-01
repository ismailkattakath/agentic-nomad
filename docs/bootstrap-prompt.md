> **Historical** — the prompt this repo was bootstrapped from (2026-10-26). Its human gate on
> every step was removed 2026-10-27; current policy lives in `.claude/rules/` and ADR-0002.

# Bootstrap prompt

The prompt this repository was scaffolded from (2026-10-26). Kept so the scaffold can be
re-derived, audited, or re-run against newer upstream docs.

```text
Scaffold a PRIVATE Claude Code project at github:ismailkattakath/agentic-nomad — a personal
agentic travel planner that finds cheap flights and lodging (hotels, Airbnb, OYO, hostels/dorms),
then books, pays, changes, cancels, tracks refunds and contacts support.

Ground truth: the 2026-10-26 research brief (Apify, booking rails, Claude plugins/MCP, prior
art, lifecycle law). Architecture = four layers, one human gate:
  SEARCH  Apify Actors (pinned via ?tools=), fli (Google Flights), Trivago, Airbnb MCP
  BOOK    Duffel (flights), LiteAPI (lodging) — the only self-serve rails with cancel/refund
  MONEY   capped single-use virtual card / Duffel balance; Stripe for refunds; refund LEDGER
  SUPPORT Gmail (draft-first), Playwright (supervised fallback), voice (later, supervised)
  GATE    every spend, cancel, outbound message and call needs the operator's explicit "yes"

Motto: off-the-shelf over hand-rolled; proven patterns; community Legos; one source of truth;
every choice names its evidence and the alternative it beat. Search before you build.

Requirements:
1. Follow CURRENT official Claude Code docs for every file shape (.mcp.json, settings.json,
   hooks, skills, subagents, rules, CLAUDE.md imports) — verify at the source, do not recall.
2. Declare MCP servers directly in project .mcp.json, version-pinned, secrets via ${ENV}
   expansion only — no `claude mcp add`, no ~/.claude.json edits, no values in git.
   (borski/travel-hacking-toolkit is NOT enabled: its owner is outside the fleet's managed
   strictKnownMarketplaces, and several of its skills drive card-issuer sites in a hidden browser.)
3. Mechanize the human gate: a PreToolUse hook (spend guard) that forces "ask" on every
   transacting MCP tool and denies live-mode keys until the operator opts in; with tests.
4. Encode policy as .claude/rules: money gate, untrusted content, OTP/3DS never read by the
   agent, refund ledger, scraping etiquette.
5. Skills for the lifecycle (trip-search, fare-watch, book-trip, cancel-and-refund,
   rights-check, support-contact) and subagents with least-privilege tool lists.
6. A Nix flake (fleet nix-dev-toolkit pattern): pinned dev shell, env catalogue + env-doctor,
   treefmt, toolchain-complete, and an OFFLINE project gate running the hook tests.
7. ADR-0001 recording the stack, every rejected option with its reason, and what could not be
   verified. Phase plan: search → sandbox booking → money → support.
8. Verify before declaring done: hook tests both ways, JSON validity, nix flake check.
   Push straight to main (operator-owned repo). No AI attribution in commits.
```

## Deviations found during execution

The prompt above is kept verbatim; these are where the scaffold differed from it, and why. Later
changes (booking direct on the supplier site, page-lab instead of Playwright, the Travel ledger
Sheet instead of a refund ledger) are recorded in ADR-0001's amendments and ADR-0002, not here.

| Prompt said | Repo does | Why |
|---|---|---|
| Apify pinned via `?tools=` in `.mcp.json` | Apify comes from the user-scope `apify` plugin | It was already installed; a second entry is a duplicate server |
| Duffel booking | Duffel is pre-gated, wrapper deferred to phase 2 | No official MCP, and the `duffel-api` SDK is archived (0.6.2, 2023) |
| `flights==0.9.0` | `flights[mcp]==0.9.0` | The bare pin exits 1 without the MCP extra (measured) |
| Stripe for refunds | Stripe over OAuth, disabled by default | Plain secret keys stop working on Stripe MCP after 2026-11-30 |
