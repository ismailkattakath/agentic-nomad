# ADR-0002 — Operating model: Claude plans, the operator decides, Google files

- **Status:** accepted after adversarial review, 2026-10-26. **Phase 0 passed**; **phase 1 built and tested** (results below); **F1 and F2 on since 2026-10-26.** Phase 0: a Workspace edition
  that includes Studio, Studio on with Gemini; Gmail smart features on.
- **Supersedes:** ADR-0001's `ledger/` — **removed** in the 2026-10-26 hygiene pass (it never held
  an entry, and the fallback if F1 fails is reading Gmail, not a JSON file).
- **Scope:** the big picture. Details get added as we **fail, find, forward** — not before.

## The problem this solves

This project exists to make travel *easier*; it must never become a second job.

- The operator works in **apps already on his phone**, not in a repo or a dashboard.
- Each fact has **one home and one writer**. No sync jobs, no second copies.
- Only **features that already exist** (Studio starters/steps, connectors). No custom code first.

## The model

```
┌──────────────────────────────────────┐
│            You: trip idea            │
└───────────────────┬──────────────────┘
                    ▼
┌──────────────────────────────────────┐
│      Claude Code: search, plan       │
└───────────────────┬──────────────────┘
                    ▼
┌──────────────────────────────────────┐
│  You approve, book on airline site   │
└───────────────────┬──────────────────┘
                    ▼
┌──────────────────────────────────────┐
│  Confirmation email lands in Gmail   │
└───────────────────┬──────────────────┘
                    ▼
┌──────────────────────────────────────┐
│ Studio flow: Gemini extracts fields  │
└───────────────────┬──────────────────┘
                    ▼
┌──────────────────────────────────────┐
│Sheet row, Drive file, Task, Chat ping│
└───────────────────┬──────────────────┘
                    ▼
┌──────────────────────────────────────┐
│  You: phone apps; agent reads Sheet  │
└──────────────────────────────────────┘
```

(The diagram shows the destination. F1 starts with the Sheet row only — see below.)

## Three roles, no overlap

| Role | Who | Does | Never does |
|---|---|---|---|
| **Planner** | Claude Code (this repo) | Research, compare, re-price, open supplier sites, explain rights, **read** the ledger | Pay, type card data, or share Google files (`share_file` is denied) |
| **Decider** | The operator | Approves every spend, pays, passes 3-D Secure, **ticks "verified"** on ledger rows | Data entry |
| **Clerk** | Workspace Studio flow F1 | Turns supplier emails into ledger rows | Decide, close, or resolve anything |

## One home per fact

| Fact | Home | Writer |
|---|---|---|
| Rules, skills, hooks, plans | This repo | Claude Code (operator reviews) |
| Live fares and drop alerts | Google Flights tracking | Google |
| **What was booked, and its final state** (one row per booking; the columns are the Sheet header) — **every trip, past and future: the forever ledger** | **"Travel ledger" Google Sheet** — private, link sharing off | **F1** for new bookings (`status = confirmed`); the 2026-10-26 backfill was the one labelled exception (`notes = backfill`) |
| **Legal refund/claim deadlines** | Computed on demand by `rights-check`; hard ones go to Calendar by the operator | Not Gemini — emails rarely state them |
| Paperwork deadlines | Google Calendar | Operator, once |

The supplier's own email is the source because it is the most authoritative record and arrives
anyway. **The Sheet header is the schema** — no separate columns note.

## F1 — file a booking (minimum viable)

| Part | Choice | Why |
|---|---|---|
| Starter | Gmail *When I get an email*, **Has the words** = booking phrases joined by `OR` (eticket, itinerary, "booking confirmed", "rental agreement", …; the live list is in Studio), no label, **Skip thread replies on** | Measured 2026-10-26: Gmail's **Travel** label missed an airline eTicket and an airline receipt; the phrase query catches both plus rail, bus and rental, at low volume. The From field rejects domains |
| Gate | **Decide** "a NEW booking, paid or reserved?" → **Check if** | Rejects schedule changes and check-in "confirmations" (tested) |
| Extract | Custom fields named exactly like the Sheet header | Reads the **email body only** (see Phase 1) |
| De-duplicate | **Get sheet contents** where `reference` = extracted reference → **Check if** *Number of matching rows* is 0 | Exact match; no second Gemini call. One booking sends several emails |
| Write | **Sheets: Add a row**: the extracted fields plus the Gmail `email_id` and the literal `status = confirmed`; `verified`, `notes`, `refund_total`, `history` empty | One writer |
| Link | The Sheet builds it: the `email_link` header cell holds one `ARRAYFORMULA` over `email_id` | Studio pads every variable with a space and writes formulas as text, so it cannot write a working link |

**Columns A (`reference`) and K (`email_id`) are formatted Plain text.** Sheets otherwise parses
values: a numeric reference such as `123456789` became a number, and a hex ID such as `18123e45…` would become scientific
notation.

**No "no" notification.** *Check if* has no else branch, and the phrase query also matches
non-travel mail, so a ping on every "no" is noise. Decide filters the query's false positives (cinema tickets, tool rentals). A missed booking is caught by `book-trip`, which
looks for the reference in the Sheet after every booking.

## The forever ledger and its backfill (2026-10-26)

The operator chose one ledger for all trips, not one per trip, so future planning starts from
history.

- **How:** three read-only Gmail passes (one per range of years) reconstructed each booking's
  **final state** from its follow-up mail (cancellations, refunds, schedule changes, credits).
  Merged and deduped, then written through the **claude.ai Google Sheets connector**
  (spend-gated: reads pass, writes ask). The browser is the last resort, kept for Studio alone,
  which has no API.
- **`status`:** `confirmed | completed | cancelled | refunded | partially_refunded | credit |
  changed | no_show | unknown`. A row with no evidence either way is `unknown`.
- **Rule for "completed":** no cancellation found **and** some trip evidence (boarding pass,
  check-in, post-stay mail). Rows resting on "no cancellation found" alone say so in `history`.
- **No-reference rows** get `NOREF-<email_id>`: a blank `reference` would make F1's dedupe match
  any future booking whose reference it fails to extract, and skip it silently.
- **One trip, several references:** an OTA booking contains an airline
  ticket F1 also filed (an airline receipt). Both rows stay; the airline row's `history` says its
  amount is included in the OTA row. **Never sum `total` without reading `history`.**
- **Recall is not 100%.** Gmail search returned no page tokens, so the three broadest queries were
  read only in part, and the backfill missed at least one receipt. A recall pass by year is the
  check; the operator decides which marginal items to add.
- **Later changes are proposed by F2, accepted by the operator** (next section).

## F2 — propose booking changes (on since 2026-10-26)

| Part | Choice | Why |
|---|---|---|
| Starter | **Subject has** change words (cancel, refund, "schedule change", voucher, "travel credit", …); thread replies **included** | Subject-only matched every real travel change plus some food/shopping/subscription noise; words in the body matched promo footers, at roughly twice the volume |
| Decide | "a CHANGE to an EXISTING travel booking?" — false for non-travel | Tested: a hotel-platform cancellation and an airline schedule change true, a food-delivery cancellation false |
| Extract | reference, change_type, refund_amount, currency, effective_date, note; input = body **+ email date** | Without the date, notes had no date |
| Match | Get sheet contents by reference → Check if rows **> 0** | No match → nothing written; the operator or agent catches it on review |
| Write | **Update rows**: `pending_change` ← note (`[type] date what`), `pending_email_id` ← email | Studio's Update rows takes **one variable per column**, so the note carries type and date |
| No match | Second branch: rows **is 0** → **Notify me by email** ("F2: travel change with no matching ledger row": reference, note, subject, sender) | A refund quoting another reference (OTA vs airline) must not vanish. Tested: an airline delay mail quoting a locator not in the ledger → alert sent; "start from emails by flows" stays off, so the alert cannot re-trigger F2 |

**F2 never touches `status`, `history`, `total` or `verified`.** It proposes; it never closes or
resolves (red-team rule). Tested end to end: only `pending_*` changed on the matched row.

**Accepting a proposal:** the agent accepts on its own when the proposal's email is from the
booking's own supplier domain and quotes the row's reference (operator, 2026-10-27); otherwise the
operator says "accept". Accepting = through the Sheets connector, set `status`, append the note to
`history` with the email id, and clear `pending_*`. **Rejecting:** clear `pending_*`. A non-empty `pending_change` is untrusted
until accepted (`untrusted-content` rule).

**Known gap:** Update rows overwrites, so two changes before review keep only the latest (Gmail
keeps both).

**Paperwork deadlines are not a flow.** `book-trip` step 9 puts each arrival form's 72-hour window
into Calendar through the Calendar connector once a flight is
booked — Studio's Calendar step is a meeting scheduler with no documented date-from-variable.

**Ledger after review (2026-10-26):** the operator removed rows that were not travel, and
confirmed some `unknown` rows from memory. Mail outside the connected account is out of the
connector's reach; a read-only browser search is the fallback.

**Why the backfill did not use F1.** F1 only fires on new mail; a past email needs one manual test
run (~30–60 s, two Gemini calls, against an unpublished daily cap), and F1 records the first
confirmation, never the final state. One run per past email costs hours and quota and still
answers less.

## F1 evaluation (2026-10-26) — past bookings and non-bookings, on a disposable copy

Run on a copy of F1 writing to a copy of the Sheet (both deleted after), compared field by field
with the ledger.

| Field | Correct | Notes |
|---|---|---|
| Decide | all | cancellations and a check-in reminder rejected |
| reference, start_date, kind | all | |
| total + currency | one miss | an airline mail without the fare |
| route_or_property | one miss | one wrong station code; several shortened to endpoints |
| supplier | two misses → **fixed** | Studio turns a domain-like name into a Markdown link in the cell. A "no links" instruction did not stop it; asking for the brand **without** the domain suffix did (`Booking`) |
| end_date | two misses → **fixed** | took a one-way flight's arrival as the end date; the description now says to leave it empty |
| refundable | two misses | one clear miss, one where F1 may be right (a rental platform) |
| change_or_cancel_deadline | mostly wrong | **a hint, never a fact** — `rights-check` owns deadlines |

Both fixes were re-verified on live F1 against emails already in the ledger, so de-duplication kept
it from writing.

**Deliberately not in F1 yet:** Drive attachments (malicious files; link-only tickets), Tasks
(date-from-variable undocumented). Each is added only when a real gap asks. Changes and refunds are
F2's job, as proposals only.

## Safety rules (from the red team)

- **Ledger rows are untrusted until the operator ticks `verified`.** A forged "confirmation" can
  steer Gemini; the agent never quotes an unverified row as fact (`untrusted-content` rule).
- **Drive sharing is denied outright** (`settings.json`). Connector writes no longer prompt
  (prompt gate removed 2026-10-27, below); the agent still asks in the conversation before a
  send, a Sheet accept or a Task strike-off (`money-gate`, `tick-checklist`).
- **Silent-miss check:** after a booking, `book-trip` looks for the reference in the Sheet (read
  only) and tells the operator if it is missing.
- **No booking reference in any future Chat ping** (reference + surname is enough to manage a
  booking).

## Amendment 2026-10-27 — autonomy on allowlisted hosts

**Decision (operator):** run the booking flow without the operator stepping in, except at money.

| Before | After |
|---|---|
| Every click, fill and key in Chromium asks | Free on an owned tab whose host is in the host allowlist (then `.claude/hooks/hosts.json`; since moved out of the repo to `${AGENTIC_NOMAD_HOSTS:-~/.config/agentic-nomad/hosts.json}`), **unless** its last snapshot showed card fields or a pay button (`page_scope.act_free`) |
| Operator types passwords and APIS fields | Logins: Apple's iCloud Passwords extension fills them from Passwords.app. Passport fields: `.claude/tools/fill-secret.mjs` fills them from the Keychain by **handle**. Neither value reaches Claude |
| Snapshots show field values | `page_scope.py` redacts secret-looking values before Claude sees them (PostToolUse `updatedToolOutput`) |

**Unchanged:** the operator's yes on every total, payment and 3-D Secure, and every OTP. The
Decider row above still holds. **Verified 2026-10-27:** a dummy secret filled on an airline site
showed as `[redacted 15 chars]` in the snapshot; the stored session transcript held it only once,
in the agent's own `secret set` command that created it — so real secrets are set by the
operator in his own terminal (`secret set` from the agent is denied). **Residuals** (judgement,
not measured): Claude Code's telemetry keeps the unredacted tool output (hooks docs); a pay step
outside `PAYMENT_RE` — e.g. a saved card shown as a radio plus a plain "Continue" button — runs
free; card fields inside a cross-origin payment iframe may not appear in a snapshot. **Rejected:** sending passport data in chat or reading the Drive
PDF (enters the transcript), a file in the repo (plaintext on disk), password-manager extension
autofill (fragile to drive, no host binding the hooks can check).

## Amendment 2026-10-27 (later) — prompt gate removed, sign-in codes automated

**Decision (operator):** "Never ask `Do you want to proceed?` at all. Unless I enter the card at
the end, no payment is going to be happening." Supersedes the click tiers of the amendment above
and the Decider row's "approves every spend" — the operator now approves by paying.

| Removed | Why it was safe to remove | What still holds |
|---|---|---|
| `spend_guard.py` (PreToolUse ask on browser and connector calls; live-key deny) | Payment needs the card the operator types; **no home profile stores a card** (checked 2026-10-27, `airline-logins`) | `money-gate`: yes in the conversation before a send, cancel or LiteAPI book |
| `permissions.ask` (Gmail send/reply/forward, Apify run) | Same: a send is still a conversational yes | `deny` rules (Drive share, raw booking-API `curl`, `secret` reveal) |
| Tab ownership tracking in `page_scope.py` | It only fed the prompts | `page_scope.py` redaction (never prompts) |
| "OTPs go to the operator" | The operator wants sign-in hands-off | 3-D Secure, bank and card codes stay his (`payment-secrets`) |

**Evidence:** in this session 84 of 211 browser calls (40%) hit an always-ask verb, 77 of them
`evaluate_script` the agent used where a free snapshot would do. **Accepted risks** (operator's
call): a hostile page can now drive clicks, sends and connector writes without a prompt — only
the conversation rules stand in its way; a stored card would turn a click into a charge; a
live API key is no longer detected. **Rejected:** keeping tiers but freeing more verbs — still
prompted on regional domains, tab switches and after every browser restart.

## Phases — fail, find, forward

0. **Eligibility** (one check): the Workspace edition includes Studio; admin has Gemini and
   Studio's service status on; Gmail smart features on. If not → stop; the agent reads Gmail
   directly instead.
1. **Build F1 and test on 3 old confirmation emails.** Pass gate: **zero manual fixes**. Also test:
   subject/sender filtering, column mapping, whether flows run with the Mac off, one live agent
   read of the Sheet.
2. **First real booking** goes through F1 (skills already read the Sheet; `ledger/` is gone).
3. Anything else only when a real failure asks for it.

## Not adopted

| Idea | Why not |
|---|---|
| Dashboard / Artifact | Second copy of Sheet + Google Flights data |
| GitHub Projects | Ceremony for a solo trip |
| Own GCP OAuth app for Sheets/Tasks | Studio does it with no client, tokens or code |
| Keep, Wallet, Photos, Music | No usable API or no role in the booking lifecycle |
| Agent files new bookings into the ledger | Two writers on one record (the agent writes only to accept an F2 proposal) |
| Gemini-extracted refund deadlines | Deadlines come from law, not emails; `rights-check` owns them |
| Flow steps documented here | Studio is the source of truth for the flow; this ADR states intent only |
| Alarm built from Calendar popups ("wake ladder") | Re-invents the phone's Clock; popups go on the day's real event (`google-reminders`) |
| Workspace advanced mobile management | Business Plus edition, work profile only, and still no alarm command |
| Google Chat API for trip pings | Needs its own Chat app in GCP; the event and tasks already carry the plan |

## Known limits (Google's help pages, read 2026-10-26)

- Gmail starter = Gmail's filter form: From, To, Subject, Has the words, Doesn't have, size,
  attachment, and **default labels only** (Important, Personal, Promotional, Purchases, Social,
  Travel). `OR` in Has the words follows Gmail filter syntax — **verified live 2026-10-26**: a self-sent
  mail matching one of the phrases started a real run within a minute; Decide rejected it.
- Starter variables expose attachment **names and types, not contents**. Extract takes text,
  a URL or a variable.
- **Max 25 flows, 25 Gmail-started, 20 steps per flow; an unpublished daily run cap** — at the cap
  flows pause until the 24 h reset. A broad starter burns runs.
- Drive **links** are not attachments. Tasks go to the primary list only.
- Sources: support.google.com/workspace-studio answers 16765661, 16444479, 16765942, 16447954.

## Adversarial review (2026-10-26)

Three independent reviews — security/money, simplicity/motto, feasibility against Google's docs.

| Finding | Severity | Resolution |
|---|---|---|
| Forged email poisons the ledger the agent trusts | High | `verified` column; unverified rows are untrusted data |
| Drive connector writes/shares with no spend gate | High | **`share_file` denied** (the `spend_guard.py` gate was removed 2026-10-27, amendment below) |
| Silent miss (odd subject, Decide = no) | High | `book-trip` checks the Sheet. The proposed Travel-label starter and "no" ping were both superseded in the build (see F1) |
| Forged "refund issued" closes a chase | High | Flows never close or resolve |
| Refund deadlines have no writer | High | `rights-check` + Calendar, not Gemini |
| Flow steps duplicated in the ADR | High | ADR states intent; Studio holds the flow |
| Repo still says `ledger/` is the source | High | Marked superseded in `CLAUDE.md` |
| F1 too big (6 steps) | Med | Minimum viable F1: Sheet row only |
| Duplicate rows per booking | Med | De-duplicate on reference before adding |
| Malicious attachments in Drive | Med | No Drive step in F1 |
| Subject OR-filter undocumented | Med | Proposed a sender filter; superseded in the build — `OR` in Has the words, verified live (see F1, Known limits) |
| Eligibility listed last | Med | Phase 0 |
| Quotas missing | Med | Added to Known limits |
| Apify schedule duplicates Google tracking | Med | **Schedule disabled**; Actor kept for ad-hoc checks |
| F2 premature | Low | Removed at review; later built as proposals-only (see F2) |

**Weakest assumption:** Gemini extracts reference and total reliably across airline email formats.
Phase 1 settled it for the body; the attachment gap remains (below).

## Phase 1 results (2026-10-26, Studio test runs on old emails)

| Email | Decide | Row | Verdict |
|---|---|---|---|
| Airline itinerary-receipt | true | every filled field matches the email | **pass** |
| Lodging booking confirmation | true | every filled field matches the email | **pass** |
| Rental agreement | true | reference, dates, place; total empty | **partial**: the total is in the PDF |
| Airline eTicket | true | reference, supplier, kind only | **partial**: the body is boilerplate, details are in the PDF |
| The same agreement again | true | "Found 1 row", nothing added | **pass** (de-duplication) |
| Airline schedule change | **false** | none | **pass** |
| Airline check-in "Confirmation" | **false** | none | **pass** |

- **No wrong value in any row.** The gap is completeness, for suppliers whose PDF holds the details.
- Defects found and fixed in the build: the email link (padded space; formulas written as text) and
  numeric parsing of IDs (plain-text columns).
- The agent reads the Sheet through the Drive connector (`read_file_content`) — tested.
