"""Tests the Claude tool-use loop WITHOUT an API key, using a pretend Claude.
The pretend Claude even tries to send an email early - the code must refuse."""
import os
from types import SimpleNamespace as NS

import agent, db, llm, seed, tools

db.init(); seed.load_sample()
os.environ["ANTHROPIC_API_KEY"] = "fake"


def tu(i, name, **inp):
    return NS(type="tool_use", id=f"t{i}", name=name, input=inp)


class FakeClient:
    def __init__(self):
        self.step = 0
        self.messages = NS(create=self.create)

    def create(self, **kw):
        self.step += 1
        if self.step == 1:
            return NS(stop_reason="tool_use", content=[tu(1, "list_attention")])
        if self.step == 2:
            return NS(stop_reason="tool_use", content=[tu(2, "draft_reminder", invoice_id="INV-1002", tone="polite",
                                                          subject="Invoice INV-1002 overdue", body="Dear team, please pay AED 2,625.")])
        if self.step == 3:
            d = db.query("SELECT id FROM drafts")[0]["id"]
            return NS(stop_reason="tool_use", content=[tu(3, "send_email", draft_id=d),   # must be refused
                                                       tu(4, "request_approval", draft_id=d),
                                                       tu(5, "draft_reminder", invoice_id="INV-1006", tone="polite",
                                                          subject="x", body="y")])      # must be refused (bad VAT)
        return NS(stop_reason="end_turn", content=[NS(type="text", text="Drafted 1 reminder, waiting for approval.")])


llm.client = lambda: FakeClient()
mode, lines = agent.run_agent()
print(mode); print(*lines, sep="\n")
assert any("refused: BLOCKED" in l for l in lines), "early send was not blocked"
assert any("refused: Cannot chase" in l for l in lines), "bad invoice was not blocked"
assert db.query("SELECT status FROM drafts")[0]["status"] == "pending_approval"
assert not db.query("SELECT 1 FROM outbox")
print("PASS: Claude loop works and the safety rules held")
db.reset(); seed.load_sample()
