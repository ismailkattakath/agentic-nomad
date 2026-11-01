# Money gate — the agent runs to the payment page; the operator pays

The agent runs **unattended** from search to the payment page — no "Do you want to proceed?"
prompts, no "yes?" in the conversation for routine steps (operator, 2026-10-27: "You can't
proceed without payment information, and that's where you wait for me").

- **The payment page is the gate.** Stop there and hand over with: total in the payment
  currency, fees, fare/rate rules, refundability, cancellation deadline, and the `fli` price
  check (`book-trip` step 3). The operator entering the card **is** the yes.
- **Re-price on the supplier's own site** before reaching that page; say if the price moved.
- **Decline upsells** (seats, insurance, bags) unless the operator asked for them.
- **Holds only while no profile stores a card** (`airline-logins`): never save a card at
  checkout. If a payment step would charge without the operator typing a card (stored card,
  points, voucher, travel credit), stop and ask.
- **Still a yes in the conversation** — things that act on the world without a card: an
  outbound email or call, a cancellation or change, a LiteAPI prebook/book, an Apify Actor not
  named in a skill. Raw `curl` to a booking API stays denied (`settings.json`).
- **Sandbox until told otherwise.** LiteAPI runs on its sandbox key; live mode is the operator's
  decision. Nothing detects a live key mechanically.
- **After a booking:** confirm it reached the "Travel ledger" Sheet (ADR-0002) before reporting
  success; if it did not, say so.
