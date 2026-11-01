---
name: rights-check
description: Work out which passenger-rights regime applies to a disrupted flight and what the traveller is owed (refund, compensation, deadlines). Use on a delay, cancellation, denied boarding, schedule change or a slow refund, or when asked "am I owed anything".
argument-hint: "<flight details or booking reference>"
---

# Rights check

Output: **regime → entitlement → deadline → how to claim**, with the source for each line.
Re-verify any number below against the cited source before quoting it in a claim — these
regimes were being amended in 2025–2026.

## Which regime

| Regime | Applies when |
|---|---|
| **Canada APPR** (SOR/2019-150) | Flight to, from or within Canada |
| **US DOT** (14 CFR 260) | Flight to, from or within the US |
| **EU261** | Departs the EU (any carrier), or arrives in the EU on an EU carrier |
| **India DGCA CAR** | Flight operated by an Indian carrier, or from India |

More than one can apply. A route between two non-EU countries on a non-EU carrier is usually **not** EU261.

## Entitlements (as researched 2026-10-26)

| Regime | Refund | Compensation | Claim deadline |
|---|---|---|---|
| APPR | within 30 days (s.18.2(2)) | large carrier delay within its control: $400 (3–6 h) / $700 (6–9 h) / $1,000 (9 h+) | 1 year |
| US DOT | automatic cash refund on cancellation or major change (3 h domestic / 6 h international): 7 business days card, 20 days other | none for delay | — |
| EU261 | 7 days | €250 / €400 / €600 by distance | national limits |
| DGCA | 7 days card; 14 working days via agent/portal (CAR eff. 2026-03-26) | denied boarding cap ≈ ₹20,000; none for delay alone | — |

Sources: `docs/adr/0001-stack.md` § Lifecycle and law.

## Then

Give the operator the due date for Calendar, and hand to `support-contact` for the claim draft.
