# Airline logins — one home program per alliance, everything else logged out

The page-lab Chromium stays **signed in only to the programs below**. Every other carrier is
booked **logged out**, with the home program's loyalty number typed into the booking form.

**Why:** every idle signed-in session is account-takeover and prompt-injection surface — a
hostile page or listing can act as the operator on any site the browser is signed in to
(`untrusted-content`). A logged-out booking still earns miles through the alliance number.

## Allowlist

One home program per alliance (Star Alliance, oneworld, SkyTeam), chosen by the operator and kept
in the operator's own notes (Drive), not here. Carriers outside an alliance and low-cost carriers
are booked logged out; ask before adding one.

**Saved cards: none** on any home-program profile. Keep it that way: a stored card lets a free
click on a pay step spend without a card field on the page (ADR-0002 residuals). Never save a
card at checkout.

**Sessions:** a Chromium restart signs out programs that use session cookies; one with
"Keep me logged in" survives. Re-sign-in costs one 2FA code each.

The **hosts** the browser may act on freely, and where a secret may be filled, live in
the operator's host allowlist, `${AGENTIC_NOMAD_HOSTS:-~/.config/agentic-nomad/hosts.json}` (one allowlist, read by the hooks and the filler; shape: `.claude/hooks/hosts.example.json`) — not here.

## How to apply

- **Before a booking**, check whether the site shows a signed-in account. Signed in to a carrier
  not on the list → tell the operator and suggest signing out; do not book in that session.
- **Logged-out booking:** ask the operator for the alliance loyalty number in the session, or
  let browser autofill supply it. Never store it in the repo, the ledger or memory.
- **Portal logins (email/username + password) come from Passwords.app** (operator,
  2026-10-27), filled by Apple's **iCloud Passwords** extension in this Chromium
  (`pejdijmoenmkgeppbflobdenhhabjlaj`). Click the email field; the extension's
  "Password AutoFill Completion List" iframe appears in the snapshot; click the matching
  account. Measured 2026-10-27: the list only appears when the tab is **in front**
  (`select_page` with `bringToFront`, then reload), and a saved username can be the field's
  label ("Email") instead of the address — check the filled username's length before Log in. No entry for the site → reset the password and let Passwords.app save it; never put
  a portal password in the Keychain (a second copy drifts).
- **Passport details come from the Keychain, by handle, never by value.** `node
  .claude/tools/fill-secret.mjs --handle travel:passport:<field> --host <host> --label "<field
  label>"` (`number`, `expiry`, `issue-country`, …) fetches the value and fills it over CDP; it
  prints only the length, and fills only on a booking or document host in the allowlist (missing allowlist → refused).
  **Split or re-laid dates:** add `--format` to the expiry handle instead of storing parts —
  `--format DD` / `MM` / `MMM` (for a "May" dropdown) / `YYYY` for three boxes, or
  `--format DD/MM/YYYY` for one box. The expiry is stored once, as `YYYY-MM-DD`.

  The operator stores each once with `secret set <handle>` **in his own terminal** (hidden
  prompt; through the agent the value would land in the transcript — denied in
  `settings.json`). A missing handle → ask the operator to set it; never fall back to
  `fill`/`type_text` with the value, `pbpaste`, or reading the Drive passport PDF. (A
  `press_key` `Meta+V` over DevTools does **not** paste — measured on an airline site, 2026-10-27.)
- **Never read a secret back:** no `secret exec`/`reveal`/`copy` from Bash (denied in
  `settings.json`), no `evaluate_script` that returns a field value, only its length.
- Reset links and verification codes in email go to the operator (`untrusted-content`,
  `payment-secrets`).
- **Creating an account** on an airline the trip needs: do it (decline marketing opt-ins), then
  report it. No yes needed (operator, 2026-10-27).
- Never sign in to a card issuer or bank in this browser (`scraping-etiquette`).
