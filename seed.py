"""Sample data: 10 FAKE invoices (fake UAE companies). Dates are relative to today so the demo always works."""
import os
from datetime import timedelta

import core
import db

# id, customer, slug, TRN, net, VAT charged, issued N days ago, due in N days (negative = overdue), paid?
ROWS = [
    ("INV-1001", "Al Noor Trading LLC (FAKE)", "alnoor-trading", "100123456700003", 4000.00, 200.00, -18, 12, False),
    ("INV-1002", "Desert Rose Catering (FAKE)", "desertrose-catering", "100234567800003", 2500.00, 125.00, -68, -38, False),
    ("INV-1003", "Gulf Breeze Logistics (FAKE)", "gulfbreeze-logistics", "100345678900003", 12000.00, 600.00, -13, 17, False),
    ("INV-1004", "Palm Crest Interiors (FAKE)", "palmcrest-interiors", "100456789000003", 3200.00, 160.00, -85, -55, False),
    ("INV-1005", "Blue Dune IT Services (FAKE)", "bluedune-it", "100567890100003", 8000.00, 400.00, -37, -8, True),
    ("INV-1006", "Marina Bright Cleaning (FAKE)", "marinabright-cleaning", "100678901200003", 1500.00, 150.00, -8, 22, False),  # VAT 10%
    ("INV-1007", "Falcon Eye Security (FAKE)", "falconeye-security", "", 5600.00, 280.00, -6, 24, False),  # missing TRN
    ("INV-1008", "Saffron Court Restaurant (FAKE)", "saffroncourt-restaurant", "100789012300003", 950.00, 47.50, -28, 2, False),
    ("INV-1009", "Oasis Print House (FAKE)", "oasis-print", "100890123400003", 2100.00, 105.00, -49, -19, True),
    ("INV-1010", "Skyline Event Rentals (FAKE)", "skyline-rentals", "100901234500003", 6400.00, 320.00, -3, 27, False),
]


ARABIC = {"INV-1002"}  # this fake customer prefers Arabic reminders


def invoice_text(inv):
    return f"""TAX INVOICE  (SAMPLE - FAKE DATA)
Invoice No: {inv['id']}
Supplier: {core.BUSINESS_NAME}
Customer: {inv['customer']}
Customer Email: {inv['email']}
Customer TRN: {inv['trn']}
Issue Date: {inv['issue_date']}
Due Date: {inv['due_date']}
Description: Office supplies and services
Amount before VAT: AED {inv['amount_excl_vat']:,.2f}
VAT: AED {inv['vat']:,.2f}
Total: AED {inv['total']:,.2f}
"""


def build():
    t = core.today()
    out = []
    for id_, cust, slug, trn, net, vat, issued, due, paid in ROWS:
        out.append({"id": id_, "customer": cust, "email": f"accounts@{slug}.example", "trn": trn,
                    "amount_excl_vat": net, "vat": vat, "total": round(net + vat, 2),
                    "issue_date": (t + timedelta(days=issued)).isoformat(),
                    "due_date": (t + timedelta(days=due)).isoformat(), "paid": paid,
                    "language": "ar" if id_ in ARABIC else "en"})
    return out


def write_sample_files():
    os.makedirs("sample_invoices", exist_ok=True)
    for inv in build():
        with open(f"sample_invoices/{inv['id']}.txt", "w", encoding="utf-8") as f:
            f.write(invoice_text(inv))
    try:  # PDF versions of a few invoices, to show real PDF reading (needs fpdf2; skipped if missing)
        from fpdf import FPDF
        os.makedirs("sample_invoices/pdf", exist_ok=True)
        for inv in build():
            if inv["id"] not in ("INV-1001", "INV-1002", "INV-1006", "INV-1007"):
                continue
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "TAX INVOICE (SAMPLE - FAKE DATA)", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 12)
            for line in invoice_text(inv).splitlines()[1:]:
                pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
            pdf.output(f"sample_invoices/pdf/{inv['id']}.pdf")
    except ImportError:
        pass


def load_sample(reset=True):
    if reset:
        db.reset()
    for inv in build():
        db.upsert_invoice(inv, source="sample")
        if inv["paid"]:
            db.run("UPDATE invoices SET state='paid' WHERE id=?", (inv["id"],))
    write_sample_files()
    db.log("system", "sample_data_loaded", "", "10 FAKE invoices loaded")


if __name__ == "__main__":
    db.init()
    load_sample()
    print("Loaded 10 fake invoices and wrote sample_invoices/*.txt")
