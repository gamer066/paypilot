"""The agent's tools. The safety rules live HERE in code, not in the prompt:
  - nothing is sent unless a human has approved that exact draft
  - invoices with errors, paid or disputed invoices can't be chased
Humans approve through human_decide(), which the AI model cannot call."""
import db
import core
import i18n

TONES = ("heads-up", "polite", "firm", "final")


def _fail(msg):
    return {"ok": False, "error": msg}


# ------------------------------------------------------------ message text
def template_reminder(inv, tone):
    """Offline wording (Claude writes its own when an API key is set)."""
    amt = f"AED {inv['total']:,.2f}"
    n, name = inv["id"], inv["customer"].replace(" (FAKE)", "")
    if inv.get("language") == "ar":
        subj, body = i18n.AR[tone]
        vals = dict(n=n, name=name, amt=amt, due=inv["due_date"], days=inv["days_overdue"])
        return subj.format(**vals), body.format(**vals) + i18n.BIZ_SIGN_AR.format(biz=core.BUSINESS_NAME)
    sign =f"\n\nKind regards,\nAccounts Team\n{core.BUSINESS_NAME}"
    if tone == "heads-up":
        return (f"Friendly reminder: invoice {n} due on {inv['due_date']}",
                f"Dear {name} team,\n\nJust a friendly heads-up that invoice {n} for {amt} is due on "
                f"{inv['due_date']}. If it is already scheduled for payment, thank you!" + sign)
    if tone == "polite":
        return (f"Invoice {n} is now overdue",
                f"Dear {name} team,\n\nOur records show invoice {n} for {amt} was due on {inv['due_date']} "
                f"and is now {inv['days_overdue']} days overdue. Could you please arrange payment? "
                f"If you have already paid, please ignore this message and accept our thanks." + sign)
    if tone == "firm":
        return (f"Second reminder: invoice {n} is {inv['days_overdue']} days overdue",
                f"Dear {name} team,\n\nWe wrote to you earlier about invoice {n} for {amt}. It is now "
                f"{inv['days_overdue']} days overdue. Please settle it within 7 days, or let us know the "
                f"date we can expect payment." + sign)
    return (f"FINAL NOTICE: invoice {n} ({amt})",
            f"Dear {name} team,\n\nInvoice {n} for {amt} is {inv['days_overdue']} days overdue and earlier "
            f"reminders have not been answered. Please pay within 3 days or call us today to agree a "
            f"plan. After this date we will need to take further steps." + sign)


# ------------------------------------------------------------ agent tools
def list_attention():
    """Which invoices need the agent's attention today, and what to do."""
    out = []
    for inv in core.all_invoices():
        base = {"invoice_id": inv["id"], "customer": inv["customer"], "total_aed": inv["total"],
                "status": inv["status"], "days_overdue": inv["days_overdue"],
                "days_to_due": inv["days_to_due"], "reminders_sent": inv["reminders_sent"],
                "language": inv.get("language", "en")}
        has_open = db.query("SELECT 1 FROM drafts WHERE invoice_id=? AND status IN "
                            "('draft','pending_approval','approved')", (inv["id"],))
        if inv["status"] == "Needs review":
            base.update(action="escalate_errors", issues=inv["issues"])
        elif inv["status"] == "Overdue":
            recent = db.query("SELECT 1 FROM drafts WHERE invoice_id=? AND status='sent' "
                              "AND sent_at >= datetime('now','localtime','-7 days')", (inv["id"],))
            if has_open or recent:
                continue  # one reminder per week at most
            n = inv["reminders_sent"]
            base["action"] = ("draft_polite", "draft_firm", "draft_final")[n] if n < 3 else "escalate_no_reply"
        elif inv["status"] == "Pending" and inv["days_to_due"] <= 3:
            seen = db.query("SELECT 1 FROM drafts WHERE invoice_id=? AND tone='heads-up'", (inv["id"],))
            if has_open or seen:
                continue
            base["action"] = "draft_heads-up"
        else:
            continue
        out.append(base)
    return {"ok": True, "invoices": out}


def check_invoice(invoice_id):
    inv = core.get_invoice(invoice_id)
    if not inv:
        return _fail(f"No invoice {invoice_id}")
    keep = ("id", "customer", "email", "trn", "amount_excl_vat", "vat", "total", "issue_date",
            "due_date", "status", "issues", "days_overdue", "days_to_due", "reminders_sent", "language")
    db.log("agent", "check_invoice", invoice_id, f"status={inv['status']}, issues={len(inv['issues'])}")
    return {"ok": True, **{k: inv[k] for k in keep}}


def draft_reminder(invoice_id, tone, subject="", body=""):
    inv = core.get_invoice(invoice_id)
    if not inv:
        return _fail(f"No invoice {invoice_id}")
    if tone not in TONES:
        return _fail(f"tone must be one of {TONES}")
    if inv["status"] not in ("Overdue", "Pending"):
        return _fail(f"Cannot chase an invoice with status '{inv['status']}'. Escalate to a human instead.")
    if db.query("SELECT 1 FROM drafts WHERE invoice_id=? AND status IN ('draft','pending_approval','approved')",
                (invoice_id,)):
        return _fail("This invoice already has a draft waiting.")
    if not subject or not body:
        subject, body = template_reminder(inv, tone)
    did = db.run("INSERT INTO drafts (invoice_id, tone, subject, body, status, created) VALUES (?,?,?,?,?,?)",
                 (invoice_id, tone, subject, body, "draft", db.now()))
    db.log("agent", "draft_reminder", invoice_id, f"tone={tone}, draft #{did}")
    return {"ok": True, "draft_id": did}


def request_approval(draft_id):
    rows = db.query("SELECT * FROM drafts WHERE id=?", (draft_id,))
    if not rows or rows[0]["status"] != "draft":
        return _fail("Draft not found or not in 'draft' state.")
    db.run("UPDATE drafts SET status='pending_approval' WHERE id=?", (draft_id,))
    db.log("agent", "request_approval", rows[0]["invoice_id"], f"draft #{draft_id} waits for a manager")
    return {"ok": True, "message": "Sent to the manager's approval queue. It will NOT be sent until approved."}


def send_email(draft_id):
    """Simulated send. Hard-blocked unless a human approved this exact draft."""
    rows = db.query("SELECT * FROM drafts WHERE id=?", (draft_id,))
    if not rows:
        return _fail("Draft not found.")
    d = rows[0]
    if d["status"] != "approved":
        db.log("system", "BLOCKED_send_email", d["invoice_id"],
               f"draft #{draft_id} is '{d['status']}', not approved - send refused")
        return _fail(f"BLOCKED: draft is '{d['status']}'. A human must approve before sending.")
    inv = core.get_invoice(d["invoice_id"])
    db.run("INSERT INTO outbox (to_addr, subject, body, draft_id, ts) VALUES (?,?,?,?,?)",
           (inv["email"], d["subject"], d["body"], draft_id, db.now()))
    db.run("UPDATE drafts SET status='sent', sent_at=? WHERE id=?", (db.now(), draft_id))
    db.log("agent", "send_email", d["invoice_id"], f"sent (simulated) to {inv['email']}: {d['subject']}")
    return {"ok": True, "message": f"Email sent (simulated) to {inv['email']}"}


def escalate_to_human(invoice_id, reason):
    open_same = db.query("SELECT 1 FROM escalations WHERE invoice_id=? AND reason=? AND status='open'",
                         (invoice_id, reason))
    if open_same:
        return {"ok": True, "message": "Already escalated."}
    db.run("INSERT INTO escalations (invoice_id, reason, created) VALUES (?,?,?)",
           (invoice_id, reason, db.now()))
    db.log("agent", "escalate_to_human", invoice_id, reason)
    return {"ok": True, "message": "A human has been alerted."}


def log_action(action, invoice_id="", detail=""):
    db.log("agent", action, invoice_id, detail)
    return {"ok": True}


# ------------------------------------------------------------ human-only
def human_decide(draft_id, approve, by="Manager", new_body=None):
    """Called only from the dashboard buttons. Never exposed to the AI."""
    rows = db.query("SELECT * FROM drafts WHERE id=?", (draft_id,))
    if not rows or rows[0]["status"] != "pending_approval":
        return _fail("Draft is not waiting for approval.")
    if new_body and new_body != rows[0]["body"]:
        db.run("UPDATE drafts SET body=? WHERE id=?", (new_body, draft_id))
        db.log(by, "edited_draft", rows[0]["invoice_id"], f"draft #{draft_id} wording changed by manager")
    db.run("UPDATE drafts SET status=?, decided_by=?, decided_at=? WHERE id=?",
           ("approved" if approve else "rejected", by, db.now(), draft_id))
    db.log(by, "approved_draft" if approve else "rejected_draft", rows[0]["invoice_id"], f"draft #{draft_id}")
    return send_email(draft_id) if approve else {"ok": True, "message": "Rejected."}


# ------------------------------------------------------------ Claude schema
SCHEMAS = [
    {"name": "list_attention",
     "description": "List invoices that need action today (overdue, due soon, or with errors) and the suggested action.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "check_invoice",
     "description": "Get full details and validation problems for one invoice.",
     "input_schema": {"type": "object", "properties": {"invoice_id": {"type": "string"}},
                      "required": ["invoice_id"]}},
    {"name": "draft_reminder",
     "description": "Write a payment reminder email draft. tone: heads-up (due soon), polite (first overdue), "
                    "firm (second), final (third). Write subject and body yourself in clear, courteous, "
                    "professional language, mention invoice number, AED amount, due date. Write in the invoice's "
                    "'language' field: 'en' = English, 'ar' = Modern Standard Arabic. Sign as the Accounts Team.",
     "input_schema": {"type": "object", "properties": {
         "invoice_id": {"type": "string"}, "tone": {"type": "string", "enum": list(TONES)},
         "subject": {"type": "string"}, "body": {"type": "string"}},
         "required": ["invoice_id", "tone", "subject", "body"]}},
    {"name": "request_approval",
     "description": "Send a draft to the human manager for approval. Always do this after drafting.",
     "input_schema": {"type": "object", "properties": {"draft_id": {"type": "integer"}},
                      "required": ["draft_id"]}},
    {"name": "send_email",
     "description": "Send an email. Only works if a human already approved the draft; otherwise it is blocked.",
     "input_schema": {"type": "object", "properties": {"draft_id": {"type": "integer"}},
                      "required": ["draft_id"]}},
    {"name": "escalate_to_human",
     "description": "Flag an invoice for a human: errors on the invoice, no reply after 3 reminders, anything unusual.",
     "input_schema": {"type": "object", "properties": {"invoice_id": {"type": "string"},
                                                       "reason": {"type": "string"}},
                      "required": ["invoice_id", "reason"]}},
    {"name": "log_action",
     "description": "Add a note to the audit log.",
     "input_schema": {"type": "object", "properties": {"action": {"type": "string"},
                                                       "invoice_id": {"type": "string"},
                                                       "detail": {"type": "string"}},
                      "required": ["action"]}},
]

REGISTRY = {f.__name__: f for f in (list_attention, check_invoice, draft_reminder, request_approval,
                                    send_email, escalate_to_human, log_action)}
