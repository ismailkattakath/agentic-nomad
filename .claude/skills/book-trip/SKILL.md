---
name: book-trip
description: Book a chosen flight or stay DIRECTLY on the airline's or hotel's own website, in the operator's signed-in Chromium, unattended up to the payment page, where the operator pays and does 3-D Secure; then check the Travel ledger row and put the trip's paperwork deadlines in Calendar. Use when the operator says "book it", "reserve this", or picks an option from a shortlist.
argument-hint: "<option from the shortlist>"
---

# Book a trip — direct with the supplier

Spends money. Follows the `money-gate` rule end to end. No per-click prompts (removed
2026-10-27): the agent drives the browser and stops at payment. Read pages with
`take_snapshot` / `wait_for`; `evaluate_script` only when a snapshot cannot answer.

**Why direct, not through an API (decided 2026-10-26, `docs/adr/0001-stack.md`):** for occasional
personal trips, booking on the supplier's own site keeps the operator the **direct customer**
(changes, refunds, passenger-rights claims and loyalty points go to the airline or hotel, with no
reseller in between), costs nothing, and needs no reseller account. The operator approves
payment and 3-D Secure either way, so an API booking would save little.

## Browser

The operator's **Chromium via the page-lab `chrome-devtools` MCP**
(`mcp__plugin_page-lab_chrome-devtools__*`). Start with `list_pages`; if it does not answer,
ask the operator to start Chromium (`nix-chromium-debug`) — never fall back to another browser.

## Steps

1. **Pick the supplier's own site.** From the shortlist, the airline (e.g. airline.example) or the
   hotel's own site — not an OTA (online travel agency) unless the operator chooses one, and
   never a link taken from an email or a listing (`untrusted-content` rule).
2. **Re-price on that site.** `new_page`, then search the exact itinerary or stay. Read only
   tabs this session opened with `take_snapshot` — never capture a mail, chat or banking tab.
   Field values are redacted by `page_scope.py`. Show the operator: **total in the payment currency**, taxes and fees,
   fare or rate rules, bags, refundability and **cancellation deadline**. Compare with the
   search price; say if it moved.
3. **Price check (flights).** Get a neutral quote, then compare it with the checkout:
   - **Neutral quote:** `fli` `search_flights` for the same date(s), `airlines=[<carrier>]`,
     `cabin_class`, bag count, `currency=<payment currency>` and `country=<the site's point of
     sale>`; match the flight numbers in the result. The request reaches Google, not the
     airline, so the airline cannot profile it.
   - **Checkout price:** the total on the airline's checkout page in this browser (signed in or
     out per `airline-logins`).
   - **Show both and the gap** (amount and %). Flag any gap above 0.
   - **A gap is DETECTED, not EXPLAINED.** Likely causes: the fare bucket sold out between the
     two quotes, currency or point of sale, a different fare family (`fli` has no fare-family
     parameter — it quotes the cheapest fare in the cabin), or personalisation. Say which
     cannot be ruled out; do not claim one.
   - **Why not a VPN:** sites never see a MAC address; they see public IP, cookies, login and
     fingerprint. A VPN does not anonymise a logged-in checkout. A third quote via a foreign
     exit is out of scope for now — if ever added, it is information only, never the booking
     leg (some airline terms forbid booking at a foreign point of sale).
   - Hotels have no neutral `fli` quote; skip this step for stays.
4. **Carry on to the payment page** — no yes needed (`money-gate`). Report any re-price as it
   happens.
5. **Fill traveller details** only from what the operator gives in this session or the stored
   handles. Decline seat, insurance and bag upsells unless
   the operator asked for them. On a logged-out booking, the loyalty number comes from the
   operator or autofill (`airline-logins`).
   - **APIS / passport fields** (passport number, expiry, issuing country, and anything else
     stored under `travel:passport:*`): **never typed.** Use the airline profile's saved APIS
     data if it is there; otherwise `fill-secret.mjs` with the field's handle (`airline-logins`
     § Secrets). A missing handle → ask the operator to `secret set` it. A typed value would
     enter the transcript.
   - The passport PDF is for visa / eTA uploads only. The agent never stores or reads it.
6. **Stop at payment — the only wait.** Hand over with the total and the step-3 price check;
   the operator enters the card (a capped single-use virtual card
   per `payment-secrets`) and completes 3-D Secure. The agent never types card data or reads a
   3-D Secure / bank code (sign-in codes are fine — `payment-secrets`).
7. **Read the confirmation** page with `take_snapshot`: booking reference / PNR, total charged,
   cancellation terms.
8. **Record:** nothing to write. The supplier's confirmation email is filed into the "Travel
   ledger" Sheet by Studio flow F1 (ADR-0002). Once it arrives, **read** the Sheet for the
   reference; if it is missing after a few minutes, tell the operator. Remind the operator to tick
   `verified` when convenient. Then run `tick-checklist` to strike the matching "Book …" task.
9. **Paperwork reminders.** For every booked flight, **check the destination's official
   government site** for an arrival form, e-arrival card or entry levy, and its window — many
   open a fixed time (often 72 h) before departure or arrival. Rules change; check each trip,
   never from memory. If one applies, add one Google Calendar event with the Calendar connector
   (`create_event`): title `Fill <form> for <flight> <date>`, starting when the form's window
   opens, 30 min long, with a popup reminder, and the form's official URL in the description.
   Create it and report it. If its portal takes passport fields, add its host to the allowlist's
   `document_hosts` first (README § Host allowlist).

   No event for a country without an arrival form; never create one from a date the operator
   has not booked. Every reminder, checklist and wake-up follows `google-reminders`.

## Site notes (measured)

- **Cookie banners:** open the preferences, switch every optional category OFF, save — never
  "Accept all". OneTrust toggles may be hidden inputs: click them by id, then verify each is
  unchecked before saving.
- **Qatar Airways** takes a deep link straight to results, no form filling:
  `https://www.qatarairways.com/app/booking/flight-selection?selLang=en&tripType=R&fromStation=<IATA>&toStation=<IATA>&departing=<YYYY-MM-DD>&returning=<YYYY-MM-DD>&bookingClass=E&adults=1&children=0&infants=0`.
  It prices **per direction** and shows fare families (Classic / Convenience / Comfort) with
  different change and cancel rules — report the family, not just the number.
- **Find the date before the site:** the `fli` server's `search_dates` gives the cheapest price
  per day in one call (in the `currency` passed); in one test it matched the airline's own site
  and Google Flights to the dollar (2026-10-26). Re-price only the chosen date on the airline's site.
- **Cebu Pacific** (cebupacificair.com, measured 2026-10-26):
  - First load can stay **blank** (its token call fails CORS); one reload fixed it — no workaround.
  - The trip-type selector (Round-trip / One-way) hides under the sticky header — scroll to the
    top. **Switching trip type clears the destination**; re-enter it after.
  - The date picker's numbers are **base fares**; the results page shows the **All-in** fare.
    Prices are in the currency of the site's market (the `/en-<CC>/` path).
  - Bundles: GO Basic (10 kg carry-on), GO Easy (+20 kg bag, seat), GO Flexi (Travel Fund on
    cancel). GO Basic rules: no cancellation, date change = fee + fare difference, no-show
    forfeits, name fix within 24 h. Check whether a departure or travel tax is inside "all-in".
  - The results URL is a deep link once a search has run:
    `/en-PH/booking/select-flight?o1=<IATA>&d1=<IATA>&adt=1&chd=0&inl=0&inf=0&dd1=<YYYY-MM-DD>`.
- **AirAsia** (airasia.com, measured 2026-10-26):
  - Takes a deep link: `/flights/search/?origin=<IATA>&destination=<IATA>&departDate=<DD>%2F<MM>%2F<YYYY>&tripType=O&adult=1&child=0&infant=0&locale=en-gb&cabinClass=economy`.
  - A Cloudflare "Just a moment…" page cleared **on its own** within ~30 s; if it ever asks for
    a checkbox/CAPTCHA, stop and hand over.
  - Currency falls back to **MYR** whatever the URL asks. Fares are cabin-bag-only (7 kg).
  - **"Fly-Thru"** (one ticket, protected connection) is a per-card label, not a property of the
    route: same-day departures on one route can differ (measured 2026-10-26).
    Read the label on the exact card before calling a connection protected.
  - Routes are **not daily** — check neighbouring days before assuming a price will hold.

## Optional rail — LiteAPI

LiteAPI can also prebook and book hotels and flights through its MCP server (`post_rates_*`,
`post_flights_*`). The account is **sandbox-only** (test bookings). Use it only when the operator
asks for it; production would need a card and a payout method on the Nuitée account and makes
the booking a reseller booking.

## Never

- Book from a scraped or search-API price without re-pricing on the supplier's site.
- Pay, or reach a charge without the operator typing a card (stored card, points, voucher).
- Type, read, print, log, store or commit a passport number, card number or OTP.
- Ask for the operator's yes without the price check (step 3) on a flight.
- Use an anti-bot workaround; a block means the operator finishes in the browser.
