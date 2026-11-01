# ADR-0001 — The stack: search wide, book on two rails, the operator pays

- **Status:** accepted, 2026-10-26. **Booking records and the operating model: see ADR-0002**
  (supersedes the refund-ledger and payment-rail parts below).
- **Evidence:** five parallel research passes (Apify census, booking rails, Claude plugins/MCP,
  prior art, lifecycle law) plus two source checks (Claude Code docs; pinned MCP invocations).
  The research brief itself is kept privately, outside this repo.

## Decision

Assemble, do not build. **No open-source or commercial product covers search → book → pay →
cancel → refund → support** for a solo developer (prior-art census). The smallest stack that can
actually transact is two self-serve rails plus off-the-shelf search, with a hook as the gate.

## Search

| Chosen | Why | Beat |
|---|---|---|
| **fli** `flights[mcp]==0.9.0` (punitarani/fli, MIT, 3.4k★) | Google Flights index, MCP entry point `fli-mcp`, no key | Apify flight Actors as primary — cost per run, one developer (`lergassy`) owns 5 of the best picks |
| **Kiwi** `mcp.kiwi.com` | Live MCP (`initialize` 200), no key, virtual interlining | Kiwi Tequila API — invite-only since 2024-05-30 |
| **Trivago** `mcp.trivago.com/mcp` | Official, no key, cross-OTA price comparison | Apify Trivago Actors — ≤7 monthly users |
| **Airbnb** `@openbnb/mcp-server-airbnb@0.3.0` | Respects robots.txt by default | HasData airbnb-mcp (8★); Airbnb has no public guest API |
| **Apify** via the user-scope `apify` plugin | One copy of the server (it is already installed); Actors: `voyager/booking-scraper` (hostels), `lergassy/google-flights-scraper` (fare calendar), `kestrel/google-hotels-prices` | A second Apify entry in `.mcp.json` — duplicate server |

## Booking rails

| Chosen | Why | Beat |
|---|---|---|
| **LiteAPI** `mcp.liteapi.travel/api/mcp` | Self-serve, free sandbox, **official MCP**, cancel endpoint, choose merchant of record; key in `X-Api-Key` header (not query string, which leaks into logs) | Expedia Rapid, Booking.com Demand, Agoda — partner contracts; Hotelbeds — certification (next step if inventory is thin) |
| **Duffel** (phase 2) | Only self-serve flight rail with order change, cancel and refund; no IATA number needed; $3/order + 1% | Amadeus Self-Service — **shut down 2026-07-17**; Sabre/Travelport/NDC — agency credentials; Skyscanner/Travelpayouts/Google — cannot book |

**Duffel has no MCP server and its Python SDK is archived** (`duffel-api` 0.6.2, 2023-10-02).
Community Duffel MCP forks (0–1★) were rejected: unaudited code holding a payment-capable token.

**Amended 2026-10-26 — LiteAPI Flights is now the first flight candidate, Duffel the fallback.**
Measured, not read: LiteAPI's MCP `tools/list` returns 95 tools, including
`post_flights_rates`, `post_flights_prebooks`, `post_flights_bookings` and
`post_flights_bookings_bookingid_cancellations`. A **sandbox** `post_flights_rates` call
(one long-haul search) returned 115 journeys with no extra access request — **but sandbox data is
mixed:** the two cheapest (the latter a nonstop that does not exist)
are a fictional test carrier, **"Nuitée Air" (ND)**; the rest are real carriers on real routings
(the cheapest on a one-stop routing). Google Flights (fli) priced that date higher,
so sandbox prices run ~23% lower than live retail — treat sandbox prices as **not live**; production flights need the account switched to production. One vendor, one official
MCP server and one key would replace a hand-written Duffel wrapper — the motto's
off-the-shelf-first choice. Open before committing: flight change/refund depth versus Duffel's
order-change API, and the merchant-of-record terms for flights. **Watch the payload:** that one
search returned 2.6 MB, so flight searches must pass `filters` (`maxStops`, time windows).

**No booking rail exists for Airbnb, OYO or Hostelworld.** They are search-and-link-out.

## Money

- Pay through the rail balance (Duffel) or a **single-use virtual card capped at the approved
  total**. Stripe Issuing supports Canada via sales; Privacy.com is US-only.
- **Stripe MCP over OAuth** (`mcp.stripe.com`, no header). Stripe MCP stops accepting full
  secret keys and untagged restricted keys after **2026-11-30**; OAuth sidesteps that.
- **Refund ledger** (`ledger/schema.json`, superseded and removed — ADR-0002): if we are seller of record, US DOT 14 CFR 260 and
  EU law make us owe the refund — deadlines must be tracked, not remembered.

## Support

Gmail connector, draft-first · the operator's Chromium via the page-lab plugin (supervised;
replaced Playwright 2026-10-26, see below) · Bland `api.bland.ai/v1/mcp`, disabled until voice is needed (`support-contact` § Phone).
Rejected: Twilio MCP (no push in 8 months), Browserbase self-host (archived), Vapi (outbound
needs an imported number; Bland's destructive tools require an explicit confirm argument).

## Amendment 2026-10-26 — book direct on the supplier's site

**Decision (operator):** search through APIs; **book on the airline's or hotel's own website in
the operator's signed-in Chromium** (page-lab `chrome-devtools` MCP), with the operator approving
each step and doing payment and 3-D Secure. LiteAPI booking stays available but optional
(sandbox only).
Which airline accounts that Chromium stays signed in to: `.claude/rules/airline-logins.md`.

| Factor | LiteAPI booking (production) | Direct, supervised Chromium |
|---|---|---|
| Money | hotels free; flights 1% (€2–€10)/ticket, €25 per voluntary change | free |
| Setup | card **and** payout method; acting as a reseller | none (page-lab already installed) |
| Customer of record | a reseller booking via Nuitée | the operator, directly |
| Refunds, APPR/DOT claims, loyalty | through the reseller; may make us seller of record | direct with the supplier |
| Payment and 3DS | operator | operator |

**Why it wins for one person, occasionally:** the human gate at payment is mandatory either way,
so API booking removes clicks, not decisions — and it costs the direct customer relationship.
Prior art agrees: browser-driven agents stop at payment. **Rejected:** Playwright
(`--isolated` cannot use the operator's signed-in sessions; a second browser path is a second
copy). **Cost:** sites change and bot checks block — a block hands checkout to the operator.
Sources: LiteAPI pricing (docs.liteapi.travel/reference/api-pricing-usage-costs, read
2026-10-26); price-index ($0.05) and places ($0.01) reads are now gated as paid calls.

## Gate

**Superseded 2026-10-27** (ADR-0002, "Amendment — prompt gate removed"): the gate is now the
card the operator types at checkout. As built until then: `spend_guard.py` (PreToolUse) asks on every non-read tool of a transacting server and denies
Duffel live tokens without `NOMAD_ALLOW_LIVE=1`. Precedent: Claude Code's documented
`permissionDecision` contract; davila7/claude-code-templates' spend-guard hook pattern.
`page_scope.py` (PostToolUse) records the Chromium tabs a session opens, and captures
(snapshot, screenshot, console, network) of any other tab ask. Its tests run as the flake's offline project gate, and fail if `.mcp.json` gains a server
nobody classified.

## Terms of service (read 2026-10-26, liteapi.travel/terms, Nuitée Travel Limited, Ireland)

- **Personal use: not addressed.** The licence is "solely to deliver travel services to your end
  users … through your travel platform". Searching for one's own trips fits that wording; it
  is a reading, not an express permission. Ask Nuitée in writing before relying on production.
- **Banned:** reselling inventory or data; scraping or bulk-downloading; building databases
  from their data outside the permitted scope; training models on it; bypassing rate limits.
- **AI agents are explicitly supported** (their own MCP server). No business/KYC clause is
  published; production needs a card on file.
- **Sandbox bookings and payments are simulated**; test card `4242 4242 4242 4242`.
- Consequence for this repo: keeping the operator's own booking records is allowed (they live in
  the "Travel ledger" Sheet since ADR-0002); do not cache LiteAPI rate results into files or a
  database.

## Not adopted

- **borski/travel-hacking-toolkit** (733★): bundles 6 MCPs + 42 skills, but its owner is outside
  the fleet's managed `strictKnownMarketplaces`, and several skills drive card-issuer and
  airline sites in a hidden browser. We declare the 4 useful servers directly instead.
- **Amadeus–Anthropic Claude toolkit:** waitlist only; booking scope unverified. Revisit.
- **Agent payment protocols** (ACP, AP2, Visa Intelligent Commerce, Mastercard Agent Pay, x402):
  no travel supplier accepts them for a solo developer yet.

## Lifecycle and law (sources)

- Canada APPR — SOR/2019-150 s.18.2(2), refund in 30 days: https://laws-lois.justice.gc.ca/eng/regulations/SOR-2019-150/FullText.html
- US DOT — 14 CFR 260: https://www.law.cornell.edu/cfr/text/14/260.6
- EU261 Art. 8: https://www.legislation.gov.uk/eur/2004/261/article/8
- India DGCA CAR (eff. 2026-03-26): https://www.scconline.com/blog/post/2026/02/27/dgca-new-airline-ticket-refund-rules-2026/
- Scraping: Ryanair v. Booking.com CFAA verdict overturned (appeal 3d Cir. 25-1374);
  Southwest v. Kiwi.com injunction on terms.

## Could not verify (weakest assumptions first)

1. **LiteAPI inventory for budget stays and hostels in the target region.** Settle with one sandbox search
   (city dorms). If thin → Hotelbeds.
2. LiteAPI MCP behaviour with a real key (header handling read in source only).
3. Kiwi MCP in Kiwi's own docs (endpoint from directories + a live `initialize` probe).
4. ~~fli via `uvx`~~ — verified 2026-10-26: answers MCP `initialize`; needs the `[mcp]` extra
   (the bare `flights==0.9.0` pin exits 1, "MCP dependencies are not installed").
5. Amadeus shutdown date and Anthropic toolkit scope (secondary sources).
6. Stripe Issuing for a Canadian individual; Mastercard Agent Pay in Canada.
