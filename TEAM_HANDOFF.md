# PayPilot - team handoff (read this first)

## What it is
AI agent that chases unpaid invoices for small UAE businesses. A human approves every message.
Hackathon: Red Rock x AUD. Online round 23 Oct 2026, finals 24 Oct.

## Links
- Website: https://paypilotai.pages.dev
- Live app: https://paypilot-agent.streamlit.app
- Code: https://github.com/gamer066/paypilot

## Run it on your laptop
```
pip install -r requirements.txt
python -m streamlit run app.py
```
Press the **One-click demo** button. Optional: put `ANTHROPIC_API_KEY=...` in a `.env` file for Claude mode.

## Where things are
| File | What it does |
|---|---|
| app.py | The dashboard (Streamlit). 6 tabs. |
| agent.py | The agent loop (Claude tool use, or offline rules), reply handling, one-click demo |
| tools.py | The agent's tools. **The safety rule lives here**: send_email refuses unless a human approved |
| core.py | Invoice checks (5% VAT, TRN), reading PDFs, risk score, cash forecast, weekly report |
| i18n.py | Arabic wording |
| db.py | SQLite. Each visitor gets a private database (sessions/), cleaned after a day |
| seed.py | The 10 FAKE sample invoices |
| docs/ | The website (one HTML file + screenshots) |
| PITCH.md, PayPilot_pitch.pptx | Pitch pack |
| test_*.py | Checks. Run all before any change |

## Rules we keep
- No new features after 19 Oct. No WhatsApp, logins, mobile apps or extra tabs.
- Demo data is FAKE only. No real customer data anywhere.
- Nothing involving money is sent without human approval.
- The public app has no API key (anyone could spend the credit).

## How to update
- App: `git push`. Streamlit Cloud redeploys by itself in about a minute.
- Website: rebuild `docs_upload.zip` (index.html + img/), then Cloudflare dashboard > Workers & Pages > paypilotai > Create deployment > upload. GitHub Pages copy updates on push.
- Screenshots for the site: `python make_screenshots.py`.

## Still open (as of 9 Oct)
1. Anthropic API key - Claude mode is only tested with a pretend Claude (test_claude_mock.py). Test live once a key exists.
2. Backup demo video - the first one (demo_backup.mp4, computer voice) was rejected. Record a new one in a human voice (record_demo.bat).
3. Practise the 3-minute pitch out loud; likely judge questions are in PITCH.md.
4. Check the slides and website on a phone.
5. Optional: show it to one real business owner and get a quote.

## Good to know
- Prices (AED 99/month) are a proposal, not a fact. The "94% of UAE companies are SMEs" stat is unverified: check before using.
- Streamlit Cloud puts free apps to sleep after a few days idle. Open the link before the demo.
