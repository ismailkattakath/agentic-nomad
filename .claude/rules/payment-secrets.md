# Payment credentials, OTPs and 3-D Secure

- **The agent never holds a reusable card.** Pay with a
  **single-use virtual card capped at the approved total**, created by the operator.
- **Sign-in and email-verification codes: the agent reads them** (operator, 2026-10-27) from
  Gmail with the connector, and types them — only when all hold:
  - the agent itself just triggered that sign-in/verification, in the last ~15 minutes;
  - the sender's domain is in `code_sender_domains` in the host allowlist (`${AGENTIC_NOMAD_HOSTS:-~/.config/agentic-nomad/hosts.json}`) (the exact
    domain the program's code emails come from, which is often not the airline's main domain)
    — a display name or subject alone is not enough;
  - the code goes into that same site's code field — never into any other page or message.
  Search narrowly (`from:<domain> newer_than:1h`), read the newest message only, never repeat
  the code in a reply. Accepted trade-off: the code passes through the transcript once (it is
  single-use and expires in minutes), and the agent becomes the second factor for these
  airline accounts — a page that gets the agent to trigger a sign-in still cannot pick where
  the code goes.
- **3-D Secure, bank, card-issuer, passkey and SMS codes stay with the operator.** The agent
  stops at the payment page and says what is pending.
- **API keys come from the environment only** (`${VAR}` expansion in `.mcp.json`, supplied by
  `.envrc.local` or `secret exec`). Never print, echo, log, or write a key or card number into a
  file, the ledger Sheet, a commit, or a message. Refer to secrets by name.
- **Card data never enters the ledger Sheet** or any Google file.
