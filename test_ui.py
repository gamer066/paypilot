"""Headless check that the dashboard runs and the main buttons work."""
from streamlit.testing.v1 import AppTest
import core, db, seed

db.init(); seed.load_sample()
print(core.extract_rules(open("sample_invoices/INV-1007.txt").read())["trn"] == "")

at = AppTest.from_file("app.py", default_timeout=30).run()
import db as _db
_db.use_session(at.session_state["sid"])
assert not at.exception, at.exception
print("loaded OK; tabs:", [t.label for t in at.tabs])
next(b for b in at.button if b.label.startswith("▶")).click()
at.run()
assert not at.exception, at.exception
print("agent ran; drafts:", db.query("SELECT COUNT(*) n FROM drafts")[0]["n"])
at.run()
ok = [b for b in at.button if b.label.startswith("✅")]
print("approve buttons:", len(ok))
ok[0].click(); at.run()
assert not at.exception, at.exception
print("outbox:", db.query("SELECT COUNT(*) n FROM outbox")[0]["n"])
