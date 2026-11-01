---
name: fare-watch
description: Watch a route or stay for a price drop, or check one now. Use when the operator says "watch this fare", "tell me if it gets cheaper", or asks whether a price moved.
argument-hint: "<route or stay> [date]"
---

# Fare watch

**Default: Google Flights "Track prices"** — free, emails the operator on drops, nothing to
maintain. In the operator's Chromium (page-lab), open the route's Google Flights results page
(`google.com/travel/flights?q=Flights to <TO> from <FROM> on <YYYY-MM-DD> one way&curr=<currency>`),
confirm the signed-in account, and switch on the **Track prices** toggle. Report which routes are
tracked.

**Check now (ad hoc):** run the Apify Actor `lergassy/google-flights-scraper` with
`calendarOnly: true`, `calendarDays: 14`, `currency: <home currency>`, `market: <home country code>`, Apify's **datacenter**
proxy (`scraping-etiquette`), and `maxTotalChargeUsd` ≤ 0.05. Say the cost first. Report the
cheapest dates; store nothing.

No scheduled scrapers and no watch files — Google's tracking already is the watch (ADR-0002).
