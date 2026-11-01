---
name: cancel-and-refund
description: Cancel or change a booking, then follow the refund or credit to completion. Use when the operator wants to cancel, change dates, check on a refund, or asks "where is my money" for a booking.
argument-hint: "<booking reference or supplier>"
---

# Cancel, change, refund

## 1. Find the booking

Read the **"Travel ledger" Sheet** (Drive connector, read-only) for the reference — trust only
rows the operator ticked `verified`. Otherwise read the supplier's confirmation in Gmail. State:
supplier, reference, what was paid, refundability, change/cancel deadline, today's date.

## 2. Quote before acting

- On the **supplier's own site** (page-lab Chromium): show what a cancel or change returns —
  cash, airline credit, or nothing — and the fee. Never assume from the fare name.
- **Airline-initiated change or cancellation:** run `rights-check` **before** accepting any
  rebooking — accepting can waive a cash refund.

## 3. Ask, then act

Explicit yes in the conversation on the exact outcome (`money-gate`).

## 4. Follow through

- The supplier's emails are the record. Studio flow F2 turns a change or refund email into a
  **proposal** in the row's `pending_change` (ADR-0002). Show it to the operator; on an explicit
  "accept", use the Sheets connector to set `status`, append the note and email id to `history`,
  and clear `pending_change`/`pending_email_id`. **Auto-accept** (no yes, operator 2026-10-27) only
  when the proposal's `pending_email_id` is from the booking's own supplier domain and its
  reference matches the row; otherwise report it as "proposed" (`untrusted-content`).
- Give the operator the **due date** from `rights-check` to put in Calendar.
- Past the due date → draft the escalation (`support-contact`), then a regulator complaint,
  then — last resort, operator decides — a chargeback.
- Credits: tell the operator the expiry date for Calendar.
