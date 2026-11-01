# No data here — this repo holds procedures; every fact lives in a Google app

Operator, 2026-10-31: neither `agentic-nomad` nor `agentic-ledger` ever holds data.

**The test:** would this line read the same for a different traveller? Yes → procedure, it may
live here. No → data, it goes to its ONE Google home, never to a repo file.

| Fact | Its one home |
|---|---|
| Trip checklist, paperwork steps, target legs | the trip's Google Tasks list |
| Timed commitments, deadlines, travel-day route | Google Calendar |
| Bookings | the "Travel ledger" Google Sheet (Studio F1/F2) |
| Live fares | Google Flights tracking |
| Documents, trip kit, research write-ups | Google Drive (PARA folders) |

The job → app mapping itself is `google-reminders.md` and the `workspace-gtd` plugin; do not
restate it. **Before writing a fact anywhere, check it is not already in its home** — a second
copy is a bug. A worked example uses fabricated values, never real ones.
`.gitleaks.toml` is the mechanical floor; it catches numbers, not prose — this rule is the rest.
