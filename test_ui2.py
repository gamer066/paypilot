from streamlit.testing.v1 import AppTest
import db, seed
db.init(); seed.load_sample()
at = AppTest.from_file("app.py", default_timeout=40).run()
assert not at.exception, at.exception
next(b for b in at.button if "One-click" in b.label).click(); at.run()
assert not at.exception, at.exception
print("demo steps:", len(at.session_state["demo_steps"]))
lang = [b for b in at.button if "Switch to" in b.label]
print("switch buttons:", len(lang))
lang[0].click(); at.run()
assert not at.exception, at.exception
print("outbox", db.query("SELECT COUNT(*) n FROM outbox")[0]["n"], "| pending", db.query("SELECT COUNT(*) n FROM drafts WHERE status='pending_approval'")[0]["n"])
