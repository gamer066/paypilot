# PayPilot
AI agent that chases unpaid invoices for small UAE businesses - with a human approving every message.
AI Agents Hackathon (Red Rock x AUD) - "Design. Deploy. Delegate."

**All data is FAKE sample data. Emails are simulated (Outbox tab).**

## Run it
```
pip install -r requirements.txt
python seed.py
python -m streamlit run app.py
```
Or double-click `run.bat`.

**Claude AI mode:** create a file called `.env` next to app.py containing
`ANTHROPIC_API_KEY=your-key-here` (or paste the key in the sidebar).
Without a key it runs in offline mode with rules, so the demo never breaks.

## 3-minute demo script
1. **Tab 1** - Upload files from `sample_invoices/` (or load samples). Show INV-1006 (VAT 10%) and INV-1007 (missing TRN) flagged orange and fixable.
2. **Tab 2** - Click *Run agent*. It writes reminders for 2 overdue invoices + a heads-up for one due soon, and sends the 2 bad invoices to a human.
3. **Tab 3** - Edit a draft, click *Approve and send*. Only now does it reach the Outbox.
4. **Tab 4** - Reply "We will pay Friday" -> status Promised. Reply "invoice is wrong" -> Disputed + human alerted.
5. **Tab 5/6** - Weekly cash report and the full audit log.

## How it works (files)
- `tools.py` - the agent's tools: list_attention, check_invoice, draft_reminder, request_approval, send_email, escalate_to_human, log_action. **Safety is enforced in code**: send_email refuses unless a human approved that draft.
- `agent.py` - Claude tool-use loop (or offline rules) + customer reply handling.
- `core.py` - validation (VAT 5%, TRN, totals), status, invoice extraction, weekly report.
- `db.py` - SQLite. `seed.py` - fake data. `app.py` - Streamlit dashboard.
- `test_flow.py`, `test_ui.py` - quick checks.
