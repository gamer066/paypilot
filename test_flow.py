"""Quick end-to-end check of PayPilot (offline mode). Run: python test_flow.py"""
import db, seed, core, agent, tools

db.init()
seed.load_sample()
for i in core.all_invoices():
    print(i["id"], i["status"], i["issues"])

mode, lines = agent.run_agent()
print("\nAGENT:", mode)
print(*lines, sep="\n")

d = db.query("SELECT id FROM drafts")[0]["id"]
r = tools.send_email(d)
assert not r["ok"], "SAFETY FAIL: sent without approval"
print("\npremature send blocked:", r["error"])
print("after approval:", tools.human_decide(d, True, "Manager"))

n_before = db.query("SELECT COUNT(*) n FROM drafts")[0]["n"]
agent.run_agent()
assert db.query("SELECT COUNT(*) n FROM drafts")[0]["n"] == n_before, "duplicate drafts"
print("second run made no duplicates")

for t in ["We will pay Friday, sorry", "This invoice is wrong, we never ordered this",
          "I already paid last week", "who is this"]:
    print(t, "->", agent.classify_rules(t)["intent"])
print(agent.handle_reply("INV-1004", "Will pay on Friday"))
print(agent.handle_reply("INV-1002", "invoice is wrong"))
print(core.report_markdown(core.build_report()))
print(core.report_narrative(core.build_report()))
for f in ["INV-1006", "INV-1007"]:
    print(core.extract_rules(open(f"sample_invoices/{f}.txt").read()))
