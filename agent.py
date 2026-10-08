"""The PayPilot agent: daily run (Claude tool use, or offline rules) and reply handling."""
import json
import re
from datetime import timedelta

import core
import db
import i18n
import llm
import tools

SYSTEM = f"""You are PayPilot, an accounts-receivable agent for {core.BUSINESS_NAME}, a small UAE company.
Your job today: chase unpaid invoices politely and safely.
Steps: call list_attention. For each invoice, follow its suggested action:
- draft_* actions: call check_invoice, then draft_reminder (tone matches the action; write a courteous,
  professional email), then request_approval with the draft id.
- escalate_errors / escalate_no_reply: call escalate_to_human with a clear reason (list the exact errors).
Rules you must follow: never try to send an email yourself before a human approves (send_email is blocked
until then). Never invent amounts or dates. Never threaten the customer. When finished, reply with a
2-3 line summary of what you did."""


def run_agent(max_steps=40):
    """Returns (mode, log_lines). Uses Claude if an API key is set, else rules."""
    db.log("agent", "run_started", "", "mode=" + ("claude" if llm.available() else "offline rules"))
    if llm.available():
        try:
            return "Claude", _run_claude(max_steps)
        except Exception as e:  # noqa: BLE001
            db.log("system", "claude_failed_fallback", "", str(e)[:200])
            lines = [f"Claude was unavailable ({str(e)[:80]}). Switched to offline rules."]
            return "rules (fallback)", lines + _run_rules()
    return "rules", _run_rules()


def _run_rules():
    lines = []
    for item in tools.list_attention()["invoices"]:
        iid, action = item["invoice_id"], item["action"]
        if action == "escalate_errors":
            reason = "Invoice has errors, cannot chase: " + "; ".join(item["issues"])
            tools.escalate_to_human(iid, reason)
            lines.append(f"{iid}: has errors, sent to a human ({'; '.join(item['issues'])})")
        elif action == "escalate_no_reply":
            tools.escalate_to_human(iid, "No payment after 3 reminders - needs a phone call")
            lines.append(f"{iid}: no payment after 3 reminders, sent to a human")
        else:
            tone = action.replace("draft_", "")
            res = tools.draft_reminder(iid, tone)
            if res["ok"]:
                tools.request_approval(res["draft_id"])
                lines.append(f"{iid}: wrote a {tone} reminder, waiting for manager approval")
            else:
                lines.append(f"{iid}: skipped - {res['error']}")
    return lines or ["Nothing needs attention today."]


def _run_claude(max_steps):
    client = llm.client()
    messages = [{"role": "user", "content": f"Today is {core.today().isoformat()}. Please run today's review."}]
    lines = []
    for _ in range(max_steps):
        resp = client.messages.create(model=llm.MODEL, max_tokens=3000, system=SYSTEM,
                                      tools=tools.SCHEMAS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            final = llm._text_of(resp)
            if final:
                lines.append("Summary: " + final)
            break
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                fn = tools.REGISTRY.get(block.name)
                try:
                    out = fn(**block.input) if fn else {"ok": False, "error": "unknown tool"}
                except TypeError as e:
                    out = {"ok": False, "error": f"bad arguments: {e}"}
                lines.append(f"{block.name}({json.dumps(block.input)[:90]}) -> "
                             f"{'ok' if out.get('ok') else 'refused: ' + str(out.get('error'))[:70]}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out)})
        messages.append({"role": "user", "content": results})
    return lines


def run_guided_demo():
    """One click: fresh fake data -> agent run -> manager approves one -> two customer replies.
    Leaves 2 reminders in the approval queue so the judge can approve them live."""
    import seed
    seed.load_sample()
    steps = ["Loaded 10 FAKE invoices"]
    _, lines = run_agent()
    steps += ["Agent: " + ln for ln in lines]
    first = db.query("SELECT id, invoice_id FROM drafts WHERE status='pending_approval' ORDER BY id")
    if first:
        tools.human_decide(first[0]["id"], True, "Manager (demo)")
        steps.append(f"Manager approved the reminder for {first[0]['invoice_id']} -> sent to the outbox")
    steps.append("Customer (INV-1004): " + handle_reply("INV-1004", "Sorry for the delay, we will pay on Friday."))
    steps.append("Customer (INV-1002, Arabic): " + handle_reply("INV-1002", "هذه الفاتورة غير صحيحة"))
    return steps


# ---------------------------------------------------------------- replies
DISPUTE = ("wrong", "incorrect", "mistake", "error", "not ours", "dispute", "did not order",
           "didn't order", "overcharg", "not correct", "never received", "not received", "too much")
PAID = ("already paid", "have paid", "has been paid", "have transferred", "already transferred",
        "payment made", "payment was made", "i paid", "we paid", "settled")
PROMISE = ("will pay", "will transfer", "will settle", "pay on", "pay by", "payment on", "payment by",
           "will send", "will make the payment", "by end of", "next week", "tomorrow")
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _promise_date(t):
    today = core.today()
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t)
    if m:
        return m.group(1)
    m = re.search(r"in (\d+) days", t)
    if m:
        return (today + timedelta(days=int(m.group(1)))).isoformat()
    if "tomorrow" in t:
        return (today + timedelta(days=1)).isoformat()
    for i, name in enumerate(DAYS):
        if name in t:
            ahead = (i - today.weekday()) % 7 or 7
            return (today + timedelta(days=ahead)).isoformat()
    if "next week" in t:
        return (today + timedelta(days=7)).isoformat()
    if "end of the month" in t or "end of month" in t:
        nxt = today.replace(day=28) + timedelta(days=4)
        return (nxt - timedelta(days=nxt.day)).isoformat()
    return (today + timedelta(days=7)).isoformat()


def classify_rules(text):
    t = text.lower()
    if any(k in text for k in i18n.AR_DISPUTE):
        return {"intent": "dispute", "promised_date": None, "summary": "Customer says the invoice is wrong (Arabic)."}
    if any(k in text for k in i18n.AR_PAID):
        return {"intent": "paid_claim", "promised_date": None, "summary": "Customer says they already paid (Arabic)."}
    if any(k in text for k in i18n.AR_PROMISE) or any(d in text for d in i18n.AR_DAYS):
        today = core.today()
        for name, idx in i18n.AR_DAYS.items():
            if name in text:
                ahead = (idx - today.weekday()) % 7 or 7
                return {"intent": "promise", "promised_date": (today + timedelta(days=ahead)).isoformat(),
                        "summary": "Customer promised to pay (Arabic)."}
        return {"intent": "promise", "promised_date": (today + timedelta(days=1 if "غد" in text else 7)).isoformat(),
                "summary": "Customer promised to pay (Arabic)."}
    if any(k in t for k in DISPUTE):
        return {"intent": "dispute", "promised_date": None, "summary": "Customer says the invoice is wrong."}
    if any(k in t for k in PAID):
        return {"intent": "paid_claim", "promised_date": None, "summary": "Customer says they already paid."}
    if any(k in t for k in PROMISE) or any(d in t for d in DAYS):
        return {"intent": "promise", "promised_date": _promise_date(t),
                "summary": "Customer promised to pay."}
    return {"intent": "other", "promised_date": None, "summary": "Unclear reply."}


def classify_reply(text):
    if llm.available():
        try:
            data = llm.ask_json(
                f"Today is {core.today().isoformat()}. A customer replied to an overdue-invoice reminder. "
                "Return JSON: intent (one of: promise, dispute, paid_claim, other), promised_date "
                "(YYYY-MM-DD or null; resolve words like 'Friday' to the next such date), summary (one line).",
                text)
            if data.get("intent") in ("promise", "dispute", "paid_claim", "other"):
                return data, "Claude"
        except Exception as e:  # noqa: BLE001
            db.log("system", "claude_classify_failed", "", str(e)[:200])
    return classify_rules(text), "rules"


def handle_reply(invoice_id, text):
    """Read a customer reply, update the invoice, escalate if needed. Returns a plain-English result."""
    res, how = classify_reply(text)
    intent = res["intent"]
    db.run("INSERT INTO replies (invoice_id, text, intent, summary, ts) VALUES (?,?,?,?,?)",
           (invoice_id, text, intent, res.get("summary", ""), db.now()))
    db.log("agent", "reply_received", invoice_id, f"intent={intent} (read by {how}): {text[:100]}")
    if intent == "promise":
        date = res.get("promised_date") or _promise_date(text.lower())
        db.run("UPDATE invoices SET promised_date=? WHERE id=?", (date, invoice_id))
        db.log("agent", "status_updated", invoice_id, f"status -> Promised until {date}")
        return f"Status updated to Promised: customer will pay by {date}. Reminders pause until then."
    if intent == "dispute":
        db.run("UPDATE invoices SET state='disputed' WHERE id=?", (invoice_id,))
        tools.escalate_to_human(invoice_id, "Customer disputes the invoice: " + text[:200])
        return "Invoice marked Disputed. Reminders stopped and a human has been alerted."
    if intent == "paid_claim":
        tools.escalate_to_human(invoice_id, "Customer says it is already paid - please check the bank account")
        return "Customer says they paid. A human must confirm in the bank before it is marked Paid."
    tools.escalate_to_human(invoice_id, "Unclear customer reply, please read: " + text[:200])
    return "Not sure what the customer means, so a human has been alerted."
