# Scraping and browser automation — low volume, official rails first

The legal risk here is mostly **breach of a site's terms and account bans**, not hacking law
(Ryanair v. Booking.com's CFAA verdict was overturned on damages; Southwest won an injunction
against Kiwi.com on terms). Airbnb's and Booking.com's terms ban bots.

- **Search, in order of preference:** official API (LiteAPI rates) → official search MCP
  (Trivago, Kiwi) → Apify Actor → community scraper MCP (fli, airbnb).
- **Booking and support forms:** the operator's own signed-in Chromium via page-lab
  (`book-trip` skill) — the operator acting for themselves, at human pace.
- **Apify runs always pass `maxTotalChargeUsd`** and use the Actors named in the `trip-search`
  and `fare-watch` skills. Never run another Actor without asking.
- **The browser runs unattended up to payment** (no per-click prompts since 2026-10-27).
  Read pages with `take_snapshot` / `wait_for`; use `evaluate_script` only when a snapshot
  cannot answer. Never sign in to a card issuer or a bank in it, and never scrape at volume.
- **No anti-bot evasion** — no residential-proxy rotation, no CAPTCHA solving, no
  fingerprint spoofing. A block is an answer: hand the link to the operator.
- **Scraped prices are snapshots.** Re-check before quoting.
