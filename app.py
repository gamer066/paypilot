"""PayPilot dashboard. Run with:  python -m streamlit run app.py"""
import os

import pandas as pd
import streamlit as st

import agent
import core
import db
import llm
import seed
import tools

st.set_page_config(page_title="PayPilot", page_icon="💸", layout="wide")
db.init()
try:  # on Streamlit Cloud the key lives in Secrets, not in the code
    if "ANTHROPIC_API_KEY" in st.secrets and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:  # noqa: BLE001 - no secrets file locally, that's fine
    pass
if not db.query("SELECT 1 FROM invoices LIMIT 1"):
    seed.load_sample(reset=False)  # fresh cloud server: start with the 10 FAKE invoices

st.markdown("""<style>
.stApp{background:radial-gradient(1200px 600px at 85% -10%,rgba(139,92,246,.18),transparent),
radial-gradient(900px 500px at 0% 100%,rgba(25,230,201,.12),transparent),#050b18}
h1{background:linear-gradient(100deg,#19e6c9,#8b5cf6 60%,#ff4d8d);-webkit-background-clip:text;background-clip:text;color:transparent!important}
[data-testid="stMetric"]{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:16px;padding:14px 18px}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px}
.stButton>button{border-radius:999px;border:1px solid rgba(255,255,255,.15);transition:.25s}
.stButton>button:hover{transform:translateY(-2px);border-color:#19e6c9;box-shadow:0 0 24px rgba(25,230,201,.3)}
button[kind="primary"]{background:linear-gradient(100deg,#19e6c9,#8b5cf6)!important;color:#04101e!important;border:0!important;font-weight:700}
.stTabs [data-baseweb="tab"]{font-weight:600}
[data-testid="stSidebar"]{background:#071022}
</style>""", unsafe_allow_html=True)

STATUS_ICON = {"Paid": "🟢 Paid", "Pending": "⚪ Pending", "Overdue": "🔴 Overdue",
               "Promised": "🟡 Promised", "Needs review": "🟠 Needs review", "Disputed": "🟣 Disputed"}

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("💸 PayPilot")
    st.caption("Design. Deploy. Delegate.")
    if llm.available():
        st.success("🧠 Claude AI mode")
    else:
        st.warning("Offline demo mode (rules). Paste an API key below for Claude AI mode.")
        key = st.text_input("Anthropic API key", type="password", help="Only kept for this session.")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key.strip()
            st.rerun()
    st.divider()
    if st.button("⚡ One-click demo", type="primary", help="Fresh data, agent run, one approval, two customer replies"):
        with st.spinner("Running the whole story..."):
            st.session_state["demo_steps"] = agent.run_guided_demo()
        st.rerun()
    if st.button("Reset and load 10 FAKE sample invoices"):
        seed.load_sample()
        st.session_state.pop("demo_steps", None)
        st.rerun()
    st.caption("All companies are FAKE sample data. Emails are simulated (see Outbox).")
    st.caption("🔒 Safety: nothing is sent until a human approves it. Every action is logged.")

st.title("💸 PayPilot")
st.caption("An AI agent that chases unpaid invoices for small UAE businesses - "
           "with a human approving every message.")

invoices = core.all_invoices()
if not invoices:
    st.info("No invoices yet. Click **Reset and load 10 FAKE sample invoices** in the sidebar, "
            "or upload invoices in tab 1.")

pending_n = db.query("SELECT COUNT(*) n FROM drafts WHERE status='pending_approval'")[0]["n"]
esc_n = db.query("SELECT COUNT(*) n FROM escalations WHERE status='open'")[0]["n"]

# Tab labels must stay constant: Streamlit jumps back to tab 1 if a label changes after a click.
tabs = st.tabs(["1 📄 Invoices", "2 🤖 Run agent", "3 ✅ Approvals",
                "4 💬 Customer replies", "5 📊 Weekly report", "6 📜 Audit log"])

# ------------------------------------------------------------------ 1 invoices
with tabs[0]:
    if "demo_steps" in st.session_state:
        with st.container(border=True):
            st.markdown("**⚡ One-click demo ran. Here is what happened:**")
            for ln in st.session_state["demo_steps"]:
                st.write("• " + ln)
            st.caption("Now open tab 3 to approve the other reminders, and tab 6 for the audit log.")
    r = core.build_report()
    c = st.columns(4)
    c[0].metric("Unpaid (AED)", f"{r['outstanding']:,.0f}")
    c[1].metric("Overdue (AED)", f"{r['overdue_total']:,.0f}")
    c[2].metric("Collected (AED)", f"{r['collected']:,.0f}")
    c[3].metric("Need a human", len(r["needs_review"]) + esc_n)
    st.metric("Expected cash in next 30 days (estimate)", f"AED {r['forecast_total']:,.0f}")

    with st.expander("📥 Upload invoices (PDF, txt, csv or json)", expanded=not invoices):
        st.caption("Try the files in `sample_invoices` (the `pdf` folder has real PDFs). The agent reads each one "
                   "and checks it. With an API key, Claude can read any invoice layout.")
        files = st.file_uploader("Invoice files", type=["pdf", "txt", "csv", "json"], accept_multiple_files=True)
        if files and st.button("Read and add these invoices"):
            for f in files:
                try:
                    for inv, how in core.parse_upload(f.name, f.getvalue()):
                        if not inv.get("id"):
                            st.error(f"{f.name}: could not find an invoice number.")
                            continue
                        db.upsert_invoice(inv, source=f.name)
                        issues = core.validate(inv)
                        db.log("agent", "invoice_extracted", inv["id"],
                               f"read from {f.name} by {how}; problems: {len(issues)}")
                        if issues:
                            st.warning(f"{inv['id']}: " + " | ".join(issues))
                        else:
                            st.success(f"{inv['id']} ({inv['customer']}): read OK, no problems")
                except Exception as e:  # noqa: BLE001
                    st.error(f"{f.name}: could not read ({e})")
            st.rerun()

    choice = st.radio("Show", ["All", "Overdue", "Pending", "Promised", "Needs review", "Disputed", "Paid"],
                      horizontal=True)
    rows = [i for i in invoices if choice == "All" or i["status"] == choice]
    if rows:
        RISK_ICON = {"High": "🔴 High", "Medium": "🟡 Medium", "Low": "🟢 Low", "Paid": "-"}
        df = pd.DataFrame([{
            "Invoice": i["id"], "Customer": i["customer"], "TRN": i["trn"] or "-",
            "Amount": i["amount_excl_vat"], "VAT": i["vat"], "Total (AED)": i["total"],
            "Due": i["due_date"], "Status": STATUS_ICON[i["status"]],
            "Risk": RISK_ICON[core.risk(i)[1]], "Language": "العربية" if i.get("language") == "ar" else "English",
            "Problems": "; ".join(i["issues"]) or "-"} for i in rows])
        st.dataframe(df, width="stretch", hide_index=True)

    bad = [i for i in invoices if i["issues"] and i["state"] == "open"]
    if bad:
        st.subheader("🟠 Fix invoices with errors")
        st.caption("The agent will not chase these until they are corrected.")
        for i in bad:
            with st.expander(f"{i['id']} - {i['customer']}"):
                for p in i["issues"]:
                    st.write("• " + p)
                a, b, c2 = st.columns(3)
                trn = a.text_input("TRN", i["trn"], key=f"trn{i['id']}")
                vat = b.number_input("VAT (AED)", value=float(i["vat"]), key=f"vat{i['id']}")
                if c2.button("Save correction", key=f"fix{i['id']}"):
                    fixed = {**i, "trn": trn.strip(), "vat": vat,
                             "total": round(i["amount_excl_vat"] + vat, 2)}
                    db.upsert_invoice(fixed, source=i["source"])
                    db.log("Manager", "corrected_invoice", i["id"], f"TRN='{trn}', VAT={vat}")
                    st.rerun()

    paid_cand = [i for i in invoices if i["state"] == "open"]
    if paid_cand:
        st.subheader("Mark as paid")
        st.caption("Only after you see the money in the bank.")
        p1, p2 = st.columns([3, 1])
        pick = p1.selectbox("Invoice", [f"{i['id']} - {i['customer']}" for i in paid_cand], label_visibility="collapsed")
        if p2.button("Mark paid"):
            iid = pick.split(" - ")[0]
            db.run("UPDATE invoices SET state='paid' WHERE id=?", (iid,))
            db.log("Manager", "marked_paid", iid, "confirmed by manager")
            st.rerun()

# ------------------------------------------------------------------ 2 agent
with tabs[1]:
    st.subheader("Let the agent review your invoices")
    st.write("The agent checks every invoice, finds overdue ones and ones due soon, writes reminders "
             "(polite first, firmer later) and sends them **to the approval queue - not to customers**. "
             "Invoices with errors or no reply after 3 reminders go to a human.")
    if st.button("▶ Run agent now", type="primary"):
        start_id = (db.query("SELECT COALESCE(MAX(id),0) m FROM audit")[0]["m"])
        with st.spinner("Agent working..."):
            mode, lines = agent.run_agent()
        st.session_state["agent_out"] = (mode, lines, start_id)
        st.rerun()
    if "agent_out" in st.session_state:
        mode, lines, start_id = st.session_state["agent_out"]
        st.success(f"Agent finished (mode: {mode}). Now open tab 3 to approve.")
        why = db.query("SELECT invoice_id, detail, actor FROM audit WHERE action='reasoning' AND id>? ORDER BY id",
                       (start_id,))
        if why:
            with st.container(border=True):
                st.markdown("**🧠 Agent reasoning**  " + (
                    "· written by Claude" if mode.startswith("Claude") else "· rule-based explanation (no API key)"))
                for w in why:
                    st.markdown(f"- {w['detail']}")
        st.markdown("**What it did**")
        for ln in lines:
            st.write("• " + ln)

# ------------------------------------------------------------------ 3 approvals
with tabs[2]:
    st.subheader("Reminders waiting for your approval")
    drafts = db.query("SELECT * FROM drafts WHERE status='pending_approval' ORDER BY id")
    st.caption(f"{len(drafts)} reminder(s) waiting · {esc_n} item(s) need a human")
    if not drafts:
        st.info("Nothing waiting. Run the agent in tab 2.")
    for d in drafts:
        inv = core.get_invoice(d["invoice_id"])
        with st.container(border=True):
            is_ar = inv.get("language") == "ar"
            st.markdown(f"**{d['invoice_id']}** · {inv['customer']} · AED {inv['total']:,.2f} · "
                        f"tone: `{d['tone']}` · language: `{'Arabic' if is_ar else 'English'}` · to: {inv['email']}")
            why = db.query("SELECT detail FROM audit WHERE action='reasoning' AND invoice_id=? ORDER BY id DESC LIMIT 1",
                           (d["invoice_id"],))
            if why:
                st.caption("🧠 Why: " + why[0]["detail"])
            st.text_input("Subject", d["subject"], key=f"sub{d['id']}", disabled=True)
            body = st.text_area("Email (you can edit before approving)", d["body"], key=f"body{d['id']}", height=190)
            a, b, c3 = st.columns([1, 1, 2])
            if c3.button("🌐 Switch to " + ("English" if is_ar else "Arabic"), key=f"lang{d['id']}"):
                db.run("UPDATE invoices SET language=? WHERE id=?", ("en" if is_ar else "ar", inv["id"]))
                inv2 = core.get_invoice(inv["id"])
                subj2, body2 = tools.template_reminder(inv2, d["tone"])
                db.run("UPDATE drafts SET subject=?, body=? WHERE id=?", (subj2, body2, d["id"]))
                db.log("Manager", "switched_language", inv["id"], f"draft #{d['id']} -> {inv2['language']}")
                st.session_state.pop(f"body{d['id']}", None)
                st.rerun()
            if a.button("✅ Approve and send", key=f"ok{d['id']}", type="primary"):
                tools.human_decide(d["id"], True, "Manager", body)
                st.rerun()
            if b.button("❌ Reject", key=f"no{d['id']}"):
                tools.human_decide(d["id"], False, "Manager")
                st.rerun()

    st.subheader("🚩 Needs a human")
    escs = db.query("SELECT * FROM escalations WHERE status='open' ORDER BY id")
    if not escs:
        st.info("No open items.")
    for e in escs:
        with st.container(border=True):
            st.markdown(f"**{e['invoice_id']}** - {e['reason']}")
            if st.button("Mark as handled", key=f"esc{e['id']}"):
                db.run("UPDATE escalations SET status='handled', handled_at=? WHERE id=?", (db.now(), e["id"]))
                db.log("Manager", "handled_escalation", e["invoice_id"], e["reason"][:100])
                st.rerun()

    st.subheader("📤 Outbox (simulated sent emails)")
    out = db.query("SELECT * FROM outbox ORDER BY id DESC")
    if out:
        for o in out:
            with st.expander(f"{o['ts']} → {o['to_addr']}: {o['subject']}"):
                st.text(o["body"])
    else:
        st.caption("No emails sent yet.")

# ------------------------------------------------------------------ 4 replies
with tabs[3]:
    st.subheader("Customer replies")
    st.write("Paste what a customer wrote back. The agent reads it, updates the invoice, "
             "and sends anything unclear or risky to a human.")
    live = [i for i in invoices if i["state"] != "paid"]
    if not live:
        st.info("No unpaid invoices.")
    else:
        names = [f"{i['id']} - {i['customer']}" for i in live]
        pick = st.selectbox("Which invoice is the reply about?", names)
        ex = st.radio("Quick examples", ["(type my own)", "We will pay Friday, sorry for the delay.",
                                          "This invoice is wrong, we never ordered this.",
                                          "I already paid this last week by bank transfer.",
                                          "سندفع يوم الجمعة إن شاء الله",
                                          "هذه الفاتورة غير صحيحة",
                                          "Who is this? Please call me."], horizontal=False)
        text = st.text_area("Customer's reply", "" if ex == "(type my own)" else ex, key=f"reply_{ex}")
        if st.button("Process reply", type="primary") and text.strip():
            result = agent.handle_reply(pick.split(" - ")[0], text.strip())
            st.success(result)
    rep = db.query("SELECT * FROM replies ORDER BY id DESC LIMIT 10")
    if rep:
        st.markdown("**Recent replies**")
        st.dataframe(pd.DataFrame(rep)[["ts", "invoice_id", "intent", "text"]], width="stretch", hide_index=True)

# ------------------------------------------------------------------ 5 report
with tabs[4]:
    r = core.build_report()
    st.subheader(f"Weekly cash summary - {r['date']}")
    st.info(core.report_narrative(r))
    c = st.columns(4)
    c[0].metric("Unpaid", f"AED {r['outstanding']:,.0f}")
    c[1].metric("Overdue", f"AED {r['overdue_total']:,.0f}")
    c[2].metric("Promised", f"AED {r['promised_total']:,.0f}")
    c[3].metric("Reminders sent (7d)", r["reminders_sent_week"])
    left, right = st.columns(2)
    with left:
        st.markdown("**Unpaid money by age (AED)**")
        st.bar_chart(pd.Series(r["buckets"]), color="#19e6c9")
    with right:
        st.markdown(f"**Expected cash, next 30 days: AED {r['forecast_total']:,.0f}**")
        st.bar_chart(pd.Series(r["forecast"]), color="#8b5cf6")
        st.caption("Estimate: paid-chance is 90% pending, 85% promised, 55% overdue, 30% with errors, 15% disputed.")
    st.download_button("⬇ Download report (Markdown)", core.report_markdown(r), "paypilot_weekly_report.md")

# ------------------------------------------------------------------ 6 audit
with tabs[5]:
    st.subheader("Audit log - every action, who did it, when")
    log = db.query("SELECT ts AS Time, actor AS Who, action AS Action, invoice_id AS Invoice, "
                   "detail AS Detail FROM audit ORDER BY id DESC")
    if log:
        df = pd.DataFrame(log)
        st.dataframe(df, width="stretch", hide_index=True)
        st.download_button("⬇ Download audit log (CSV)", df.to_csv(index=False), "paypilot_audit_log.csv")
    else:
        st.info("Nothing logged yet.")
