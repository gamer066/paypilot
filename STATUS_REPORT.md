# PayPilot - full status (9 Oct 2026)

## Links (all live)
- Website: https://paypilotai.pages.dev (backup copy: https://gamer066.github.io/paypilot/)
- Live app: https://paypilot-agent.streamlit.app (offline mode, fake data)
- Code (public): https://github.com/gamer066/paypilot

## What the app does
- Reads invoices (PDF, txt, csv, json) and checks them: 5% VAT, TRN, totals, dates.
- Agent finds overdue and due-soon invoices, writes reminders (heads-up, polite, firm, final), max one a week.
- "Agent reasoning" box explains why it chose each tone or escalation.
- Human approval queue: edit, switch Arabic/English, approve. Nothing sends before that (enforced in code, tested).
- Customer replies (English + Arabic): promise, dispute, already paid, unclear. Updates status or alerts a human.
- Risk score per invoice, 30-day cash forecast, weekly cash summary (download), full audit log (download).
- One-click demo button in the sidebar. Claude mode with an API key; offline rules mode without.
- Emails are simulated (outbox). Real email sending was considered and SKIPPED (his choice).

## Quality checks done
- test_flow.py, test_features.py, test_ui.py, test_ui2.py, test_claude_mock.py all pass.
- Live app checked after deploy: one-click demo runs.
- Bug found by recording the demo and fixed: tab jumped back to tab 1 after Approve.

## Pitch material
- PayPilot_pitch.pptx (8 slides incl. business model), PITCH.md (description, 3-min script, Q&A, checklist).
- demo_backup.mp4 (2 min, computer voice). Salman does NOT like it (reason not given). Can be redone.
- Business model: AED 99/month is a PROPOSED price. The "94% of UAE companies are SMEs" stat is unverified, not used.

## Not done / needs Salman
1. Anthropic API key (needs phone code + card) - Claude mode untested live; mock test only.
2. Tell me what is wrong with the demo video, or record his own voice with record_demo.bat.
3. Look at the slides and the website on his phone (not visually checked).
4. Show the app to one real business owner and get a quote (optional, strong).
5. Click Submit on the hackathon form with the links.
6. Open the live app link once before 23 Oct so it is awake.

## Dates
- 19 Oct: stop adding features. 22 Oct: final check + video ready. 23 Oct: online round. 24 Oct: finals at AUD (top 10).

## How to update things
- App: push to GitHub, Streamlit Cloud redeploys by itself.
- Website: rebuild docs_upload.zip, upload in Cloudflare dashboard (paypilotai > Create deployment). GitHub Pages copy updates on push.
- Re-record video: python make_demo_video.py. Retake screenshots: python make_screenshots.py.
