# PayPilot - hackathon pack

## One-line pitch
PayPilot is an AI agent that chases unpaid invoices for small UAE businesses, and never sends a message without a human approving it.

## Submission description (paste into the form)
PayPilot takes over the repetitive job of chasing late invoices. It reads invoices and validates them (5% UAE VAT, TRN, totals), watches due dates, drafts reminders that get firmer over time, and reads customer replies ("will pay Friday" updates the status; "invoice is wrong" goes to a human). A manager approves every email before it is sent - this rule is enforced in code, so the agent cannot send on its own. Every action is recorded in an audit log, and a weekly cash summary is generated automatically. Built with Python, Streamlit, SQLite and the Claude API (tool use). All demo data is fake.

## 3-minute demo script
**0:00 - Problem (20s).** "Small businesses lose hours chasing late invoices. PayPilot does it, but you stay in control."
**0:20 - Invoices (30s).** Tab 1. Upload files from `sample_invoices`. Point at INV-1006 (VAT 10%) and INV-1007 (missing TRN): "It catches mistakes before anyone chases a customer."
**0:50 - Agent (40s).** Tab 2, click Run agent. "Two overdue invoices get polite reminders, one due-soon gets a heads-up. The two bad invoices go to a human."
**1:30 - Approval (40s).** Tab 3. Edit one line, click Approve. Open the Outbox. "Nothing left the building until I clicked. Even if the AI tried, the code refuses."
**2:10 - Replies (30s).** Tab 4. "We will pay Friday" -> Promised. "This invoice is wrong" -> Disputed + human alerted.
**2:40 - Report + audit (20s).** Tabs 5 and 6. "Weekly cash summary, and a log of every action."

## 3 key points
1. Human approval is enforced in code, not just in the prompt.
2. It handles the whole loop: intake, validation, reminders, replies, reports.
3. Every action is logged, and hard cases go to a human.

## Likely judge questions
- **Why not just a template email tool?** It validates invoices, picks the tone from history, reads replies, and decides when to stop and call a human.
- **What if the AI makes a mistake?** It can only draft. A person approves and can edit. Invoices with errors are never chased.
- **Is data safe?** Demo uses fake data only. Next step is a pilot with permission and real email integration.
- **What if Claude is down?** It falls back to offline rules and keeps working.
- **How would it make money?** Monthly subscription per business, or a small fee on recovered invoices.

## Backup demo video (record by 22 Oct)
Record your screen with the Windows Game Bar (Win + G) or OBS while following the script above. Keep it under 3 minutes.

## Before the day
- [ ] Get an Anthropic API key, put it in `.env`, run the demo once in Claude mode
- [ ] Run `run.bat` fresh before presenting (it resets to the fake data)
- [ ] Have the backup video and `PayPilot_pitch.pptx` open
- [ ] Charge the laptop, check wifi
