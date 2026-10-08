"""Checks the new features: PDF reading, Arabic, risk, forecast, one-click demo."""
import io, os
import agent, core, db, seed, tools

db.reset(); seed.load_sample()

# 1. PDF reading
for f in ("INV-1006", "INV-1007", "INV-1001"):
    raw = open(f"sample_invoices/pdf/{f}.pdf", "rb").read()
    (inv, how), = core.parse_upload(f + ".pdf", raw)
    print(f, how, inv["customer"], inv["total"], "TRN=", repr(inv["trn"]), "->", core.validate(inv))
(inv, _), = core.parse_upload("x.pdf", open("sample_invoices/pdf/INV-1007.pdf", "rb").read())
assert core.validate(inv) and "Missing TRN" in core.validate(inv)[0]

# 2. Arabic template + replies
inv = core.get_invoice("INV-1002")
assert inv["language"] == "ar"
subj, body = tools.template_reminder(inv, "polite")
assert any("؀" <= c <= "ۿ" for c in body), "no Arabic in body"
print("Arabic subject OK:", len(subj), "chars")
for t, want in [("سندفع يوم الجمعة", "promise"), ("هذه الفاتورة غير صحيحة", "dispute"),
                ("تم الدفع بالفعل", "paid_claim"), ("Will pay Friday", "promise")]:
    got = agent.classify_rules(t)["intent"]
    assert got == want, (t, got)

# 3. risk + forecast
for i in core.all_invoices():
    print(i["id"], i["status"], core.risk(i)[:2])
weeks, total = core.forecast()
print("forecast", {k: round(v) for k, v in weeks.items()}, round(total))
assert total > 0

# 4. one-click demo
steps = agent.run_guided_demo()
print(*steps, sep="\n")
assert db.query("SELECT COUNT(*) n FROM outbox")[0]["n"] == 1
assert db.query("SELECT COUNT(*) n FROM drafts WHERE status='pending_approval'")[0]["n"] >= 1
print("ALL OK")
db.reset(); seed.load_sample()
