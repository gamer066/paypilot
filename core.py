"""PayPilot core logic: validation, status, invoice extraction, weekly report."""
import csv
import io
import json
import re
from datetime import date, timedelta

import db
import llm

VAT_RATE = 0.05
BUSINESS_NAME = "Sandstone Office Supplies LLC (FAKE)"


def today():
    return date.today()


def _d(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- validation
def validate(inv):
    """Return a list of problems with an invoice (empty list = looks fine)."""
    issues = []
    net, vat, total = (inv.get("amount_excl_vat") or 0), (inv.get("vat") or 0), (inv.get("total") or 0)
    trn = (inv.get("trn") or "").strip()
    if not (inv.get("customer") or "").strip():
        issues.append("Missing customer name")
    if not (inv.get("email") or "").strip():
        issues.append("Missing customer email")
    if not trn:
        issues.append("Missing TRN (Tax Registration Number)")
    elif not re.fullmatch(r"\d{15}", trn):
        issues.append(f"TRN '{trn}' is not 15 digits")
    if net <= 0:
        issues.append("Amount is missing or zero")
    else:
        expected = round(net * VAT_RATE, 2)
        if abs(vat - expected) > 0.02:
            issues.append(f"VAT is AED {vat:,.2f} ({vat / net * 100:.1f}%) but UAE VAT is 5% = AED {expected:,.2f}")
        if abs(net + vat - total) > 0.02:
            issues.append(f"Total AED {total:,.2f} does not equal amount + VAT (AED {net + vat:,.2f})")
    issue, due = _d(inv.get("issue_date")), _d(inv.get("due_date"))
    if not due:
        issues.append("Missing or invalid due date")
    elif issue and due < issue:
        issues.append("Due date is before the issue date")
    return issues


def status_of(inv, issues):
    if inv["state"] == "paid":
        return "Paid"
    if inv["state"] == "disputed":
        return "Disputed"
    if issues:
        return "Needs review"
    promised = _d(inv.get("promised_date"))
    if promised and promised >= today():
        return "Promised"
    due = _d(inv["due_date"])
    return "Overdue" if due < today() else "Pending"


def sent_reminders(invoice_id):
    rows = db.query("SELECT COUNT(*) n FROM drafts WHERE invoice_id=? AND status='sent' "
                    "AND tone IN ('polite','firm','final')", (invoice_id,))
    return rows[0]["n"]


def enrich(row):
    inv = dict(row)
    inv["issues"] = validate(inv)
    inv["status"] = status_of(inv, inv["issues"])
    due = _d(inv.get("due_date"))
    delta = (today() - due).days if due else 0
    inv["days_overdue"] = max(delta, 0)
    inv["days_to_due"] = max(-delta, 0)
    inv["reminders_sent"] = sent_reminders(inv["id"])
    return inv


def all_invoices():
    return [enrich(r) for r in db.query("SELECT * FROM invoices ORDER BY id")]


def get_invoice(invoice_id):
    rows = db.query("SELECT * FROM invoices WHERE id=?", (invoice_id,))
    return enrich(rows[0]) if rows else None


# ---------------------------------------------------------------- extraction
def _num(s):
    m = re.search(r"-?\d[\d,]*\.?\d*", s or "")
    return float(m.group(0).replace(",", "")) if m else 0.0


def _field(text, *labels):
    for label in labels:
        m = re.search(rf"^[ \t]*{label}[ \t]*[:\-][ \t]*(.*?)[ \t]*$", text, re.I | re.M)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return ""


def extract_rules(text):
    """Offline extraction: reads 'Label: value' lines from a text invoice."""
    return {
        "id": _field(text, "Invoice No", "Invoice Number", "Invoice #", "Invoice"),
        "customer": _field(text, "Customer", "Bill To", "Client"),
        "email": _field(text, "Customer Email", "Email"),
        "trn": re.sub(r"\D", "", _field(text, "Customer TRN", "TRN", "Tax Registration Number")),
        "issue_date": _field(text, "Issue Date", "Invoice Date", "Date"),
        "due_date": _field(text, "Due Date", "Payment Due"),
        "amount_excl_vat": _num(_field(text, "Amount before VAT", "Subtotal", "Net Amount")),
        "vat": _num(_field(text, "VAT", "VAT Amount")),
        "total": _num(_field(text, "Total", "Total Amount", "Grand Total")),
    }


def extract_invoice(text):
    """Use Claude to read any invoice text; fall back to simple rules."""
    if llm.available():
        try:
            data = llm.ask_json(
                "You extract data from invoices. Return ONLY JSON with keys: id, customer, email, "
                "trn (digits only, empty string if missing), issue_date (YYYY-MM-DD), due_date "
                "(YYYY-MM-DD), amount_excl_vat (number), vat (number), total (number). "
                "Never invent values: use empty string or 0 if the invoice does not show it.", text)
            if data.get("id"):
                data["trn"] = re.sub(r"\D", "", str(data.get("trn") or ""))
                return data, "Claude"
        except Exception as e:  # noqa: BLE001 - fall back quietly
            db.log("system", "claude_extract_failed", "", str(e)[:200])
    return extract_rules(text), "rules"


def parse_upload(name, raw):
    """Turn an uploaded file into a list of (invoice dict, method) pairs."""
    if name.lower().endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        if not text.strip():
            raise ValueError("this PDF has no readable text (it may be a scan)")
        return [extract_invoice(text)]
    text = raw.decode("utf-8", errors="ignore")
    if name.lower().endswith(".json"):
        data = json.loads(text)
        return [(i, "json") for i in (data if isinstance(data, list) else [data])]
    if name.lower().endswith(".csv"):
        out = []
        for r in csv.DictReader(io.StringIO(text)):
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items()}
            for k in ("amount_excl_vat", "vat", "total"):
                r[k] = _num(r.get(k, ""))
            out.append((r, "csv"))
        return out
    return [extract_invoice(text)]


# ---------------------------------------------------------------- risk + forecast
# Simple, explainable estimates (not machine learning): chance an invoice is paid within 30 days.
PAY_CHANCE = {"Pending": 0.90, "Promised": 0.85, "Overdue": 0.55, "Needs review": 0.30, "Disputed": 0.15}


def risk(inv):
    """Returns (score 0-100, label, why). Higher = more likely to be paid late or never."""
    if inv["status"] == "Paid":
        return 0, "Paid", ""
    score, why = 0, []
    if inv["days_overdue"]:
        score += min(55, inv["days_overdue"])
        why.append(f"{inv['days_overdue']} days late")
    if inv["reminders_sent"]:
        score += 10 * inv["reminders_sent"]
        why.append(f"{inv['reminders_sent']} reminder(s) sent")
    if inv["status"] == "Disputed":
        score += 35
        why.append("disputed")
    if inv["status"] == "Needs review":
        score += 20
        why.append("invoice has errors")
    if inv["total"] >= 10000:
        score += 10
        why.append("large amount")
    if inv["status"] == "Promised":
        score = max(score - 20, 5)
        why.append("customer promised")
    score = min(score, 100)
    label = "High" if score >= 60 else "Medium" if score >= 30 else "Low"
    return score, label, ", ".join(why) or "on time"


def forecast():
    """Expected cash in the next 30 days, by week. Returns (rows, total)."""
    weeks = {"This week": 0.0, "Week 2": 0.0, "Week 3": 0.0, "Week 4": 0.0}
    for inv in all_invoices():
        if inv["status"] == "Paid":
            continue
        amount = inv["total"] * PAY_CHANCE.get(inv["status"], 0.5)
        if inv["status"] == "Promised":
            d = (_d(inv["promised_date"]) - today()).days
        elif inv["status"] == "Overdue":
            d = 10  # overdue invoices: assume it takes about 10 days after we chase
        else:
            d = inv["days_to_due"] + 5  # customers usually pay a few days after the due date
        d = max(d, 0)
        key = "This week" if d <= 7 else "Week 2" if d <= 14 else "Week 3" if d <= 21 else "Week 4" if d <= 30 else None
        if key:
            weeks[key] += amount
    return weeks, sum(weeks.values())


# ---------------------------------------------------------------- report
def build_report():
    invs = all_invoices()
    open_ = [i for i in invs if i["status"] != "Paid"]
    overdue = [i for i in invs if i["status"] == "Overdue"]
    week_ago = (today() - timedelta(days=7)).isoformat()
    sent = db.query("SELECT COUNT(*) n FROM drafts WHERE status='sent' AND sent_at >= ?", (week_ago,))[0]["n"]
    buckets = {"Not due yet": 0.0, "1-30 days late": 0.0, "31-60 days late": 0.0, "60+ days late": 0.0}
    for i in open_:
        d = i["days_overdue"]
        key = ("Not due yet" if d == 0 else "1-30 days late" if d <= 30
               else "31-60 days late" if d <= 60 else "60+ days late")
        buckets[key] += i["total"]
    promised = [i for i in invs if i["status"] == "Promised"]
    return {
        "date": today().isoformat(),
        "outstanding": sum(i["total"] for i in open_),
        "overdue_total": sum(i["total"] for i in overdue),
        "overdue_count": len(overdue),
        "collected": sum(i["total"] for i in invs if i["status"] == "Paid"),
        "promised_total": sum(i["total"] for i in promised),
        "promised_count": len(promised),
        "disputed": [i["id"] for i in invs if i["status"] == "Disputed"],
        "needs_review": [i["id"] for i in invs if i["status"] == "Needs review"],
        "reminders_sent_week": sent,
        "awaiting_approval": db.query("SELECT COUNT(*) n FROM drafts WHERE status='pending_approval'")[0]["n"],
        "open_escalations": db.query("SELECT COUNT(*) n FROM escalations WHERE status='open'")[0]["n"],
        "buckets": buckets,
        "forecast": forecast()[0],
        "forecast_total": forecast()[1],
        "top_overdue": sorted(overdue, key=lambda i: -i["total"])[:5],
    }


def report_markdown(r):
    lines = [f"# PayPilot weekly cash summary - {r['date']}", "",
             f"- **Outstanding (unpaid):** AED {r['outstanding']:,.2f}",
             f"- **Overdue:** AED {r['overdue_total']:,.2f} ({r['overdue_count']} invoices)",
             f"- **Collected (paid):** AED {r['collected']:,.2f}",
             f"- **Promised by customers:** AED {r['promised_total']:,.2f} ({r['promised_count']} invoices)",
             f"- **Reminders sent in last 7 days:** {r['reminders_sent_week']}",
             f"- **Waiting for manager approval:** {r['awaiting_approval']}",
             f"- **Open items for a human:** {r['open_escalations']}",
             f"- **Disputed:** {', '.join(r['disputed']) or 'none'}",
             f"- **Invoices with errors (cannot chase yet):** {', '.join(r['needs_review']) or 'none'}",
             "", "## Money by age"]
    lines += [f"- {k}: AED {v:,.2f}" for k, v in r["buckets"].items()]
    lines += ["", f"## Expected cash, next 30 days (estimate): AED {r['forecast_total']:,.2f}"]
    lines += [f"- {k}: AED {v:,.2f}" for k, v in r["forecast"].items()]
    lines += ["", "## Biggest overdue invoices"]
    lines += [f"- {i['id']} {i['customer']}: AED {i['total']:,.2f}, {i['days_overdue']} days late"
              for i in r["top_overdue"]] or ["- none"]
    return "\n".join(lines)


def report_narrative(r):
    """One short plain-English paragraph for the business owner."""
    facts = report_markdown(r)
    if llm.available():
        try:
            return llm.ask_text("You write short cash-flow updates for a small business owner. "
                                "3-4 plain sentences, no jargon, say what needs attention first. "
                                "Use only the facts given.", facts)
        except Exception:  # noqa: BLE001
            pass
    bits = [f"AED {r['outstanding']:,.0f} is still unpaid, and AED {r['overdue_total']:,.0f} of it is overdue."]
    if r["promised_total"]:
        bits.append(f"Customers have promised AED {r['promised_total']:,.0f}.")
    if r["awaiting_approval"]:
        bits.append(f"{r['awaiting_approval']} reminder(s) are waiting for your approval.")
    if r["open_escalations"] or r["needs_review"]:
        bits.append("Some items need a person to look at them.")
    return " ".join(bits)
