# PayPilot status report (9 Oct 2026) - for the planning session

## Done
- **Step 1-6 built, and more:** fake data (10 invoices), invoice upload + validation (5% VAT, TRN, totals), agent with tools (list_attention, check_invoice, draft_reminder, request_approval, send_email, escalate_to_human, log_action), approval queue, customer reply handling + escalation, weekly report, audit log. Python + Streamlit + SQLite + Claude tool use, with offline-rules fallback.
- **Safety enforced in code:** send_email refuses unless a human approved that draft (tested). Invoices with errors, disputes and silent customers go to a human. One reminder per week max.
- **Tests pass:** test_flow.py, test_ui.py (dashboard), test_claude_mock.py (Claude loop with a pretend Claude; early send was blocked).
- **Bug found and fixed while recording:** dashboard jumped back to tab 1 after clicking Approve. Fixed and pushed.
- **Online:**
  - Website (animated, scroll effects, in-page demo): https://paypilotai.pages.dev
  - Live app (Streamlit Cloud, offline mode, fake data): https://paypilot-agent.streamlit.app
  - Code (public): https://github.com/gamer066/paypilot
- **Pitch pack:** PayPilot_pitch.pptx (7 slides), PITCH.md (description to paste, 3-min script, Q&A, checklist).
- **Backup demo video:** demo_backup.mp4 (about 2.5 min, voice-over + captions), recorded by script (make_demo_video.py).

## Not done / only Salman can do
1. **Anthropic API key** - not obtained (console needs phone code + card). Claude mode is untested live (only with a mock). Offline mode works.
2. **Eyeball the slides** and the website on a phone - not visually checked.
3. **Submit** on the hackathon site with the links above (he clicks Submit).
4. Open the live app link once before 23 Oct so it is not asleep.

## Decisions made
- Landing site on Cloudflare Pages as paypilotai.pages.dev (paypilot.pages.dev is taken; Salman rejected the long name).
- No API key in the public app (anyone could spend credit); Claude mode only on his laptop.
- To update the website: re-upload docs_upload.zip in the Cloudflare dashboard (direct upload, not git).

## Timeline
- 8-9 Oct: built, deployed, video.
- By 19 Oct: freeze features, practise demo.
- 22 Oct: final check, backup video ready.
- 23 Oct: online round. 24 Oct: finals at AUD if in top 10.
