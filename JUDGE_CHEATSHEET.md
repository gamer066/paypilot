# PayPilot - judge cheat sheet (simple words)

## 1. One sentence
PayPilot is an AI helper that chases late invoices for small businesses, and a person approves every message before it goes out.

## 2. Thirty seconds
Small businesses lose time and money chasing late payments. PayPilot reads the invoices, checks them for mistakes, writes polite reminders, and waits for the owner to click Approve. Only then does it send. It also reads customer replies, writes a weekly cash report, and keeps a log of everything it did.

## 3. Three things to remember
1. **A person always approves.** The rule is in the code, so even the AI cannot skip it.
2. **It does the whole job**: check invoices, find late ones, write reminders, read replies, report.
3. **Everything is logged**, and hard cases go to a human.

## 4. Demo in 5 clicks (3 minutes)
1. Press **One-click demo** (top of the app). Say: "Fake data, the agent just did a day of work."
2. Tab 1: point at the two orange invoices. "Wrong VAT and missing tax number. It will not chase these."
3. Tab 3: open a reminder, read the "Why" line, click **Approve and send**. "Only now does it send."
4. Tab 4: pick "We will pay Friday". "It updates the status by itself."
5. Tab 6: show the audit log. "Every action, who, when."

## 5. Questions judges may ask (short answers)
**Is it really AI, or just rules?**
It uses Claude to read invoices, write reminders and read replies. The safety rules are normal code on purpose, because rules must never be guessed. Without internet or a key it falls back to simple rules, so the demo never breaks.

**What if the AI makes a mistake?**
It can only draft. A person reads, edits and approves. Invoices with errors are never chased.

**What stops it emailing someone by accident?**
The send step checks "was this approved by a human?" and refuses if not. It also writes the refusal to the log.

**Where does the data go? Is it safe?**
The demo uses fake data only. Each visitor gets their own private copy that is deleted after a day. The public app has no API key.

**Why not just use a template or Outlook rules?**
Templates do not check the invoice, pick the tone from history, understand replies, or know when to stop and call a person.

**Who is the customer?**
Small UAE businesses that invoice on credit: trading, catering, cleaning, services.

**How does it make money?**
Proposed price: AED 99 per month per business. One recovered AED 3,000 invoice pays for a year. (This is a plan, not proven yet.)

**Does it work in Arabic?**
Yes. Reminders can be written in Arabic or English, and it understands Arabic replies.

**Can it read real invoices?**
Yes, PDFs, plus text, CSV and JSON files. Scanned photos are not supported yet.

**What is the cash forecast?**
A simple estimate of what will be paid in the next 30 days, using how likely each kind of invoice is to be paid. It is labelled as an estimate.

**Why is this not already on the market?**
Accounting tools do have basic automatic reminders. PayPilot goes further: it checks the invoice first, picks the tone from history, reads the replies, keeps a person in charge, and logs everything. It also writes in Arabic. (Do not say nobody does this. If asked about a specific tool, say you compared the basics and would test properly in a pilot.)

**What is the difference between your idea and a real business?**
The idea is the agent. The business is selling it to small companies for a monthly fee, reaching them through accountants and small business groups, and proving it by recovering real invoices. We have not tested with real customers yet. That is the next step.

**What about legal and privacy rules?**
The demo uses fake data. For real customers we would check UAE VAT rules and data protection rules first, keep each business's data separate, and keep the human approval and the log.

**What did you build in this hackathon?**
Everything: the agent and its tools, the safety gate, invoice checks, PDF reading, Arabic, approval screen, reports, audit log, and the website.

**What would you do next?**
Send real emails after approval, connect to accounting software, add WhatsApp, and pilot with a few real businesses.

**What is not finished?**
Real email sending is simulated for safety. Claude mode needs an API key; the public demo runs in simple-rules mode.

## 6. Numbers that are safe to say
- 10 sample invoices, all fake.
- 7 agent tools.
- 5% UAE VAT is checked on every invoice.
- 1 reminder per invoice per week at most.
- Do **not** quote market statistics (like how many UAE businesses are SMEs) unless you checked them.

## 7. If something goes wrong on stage
- App asleep or slow: open the website (paypilotai.pages.dev); its demo runs in the page and needs nothing.
- Wifi down: run it on the laptop (`run.bat`) or play the backup video.
- Press **Reset and load 10 FAKE sample invoices** in the sidebar to start clean.
