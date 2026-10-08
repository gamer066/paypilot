"""Claude connection. If there is no API key, PayPilot runs in offline demo mode."""
import json
import os
import re

MODEL = os.environ.get("PAYPILOT_MODEL", "claude-sonnet-5-5")


def _load_dotenv():
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def client():
    import anthropic
    return anthropic.Anthropic()


def _text_of(resp):
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def ask_text(system, user, max_tokens=600):
    resp = client().messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                    messages=[{"role": "user", "content": user}])
    return _text_of(resp)


def ask_json(system, user):
    out = ask_text(system + " Reply with JSON only.", user, max_tokens=800)
    m = re.search(r"\{.*\}", out, re.S)
    return json.loads(m.group(0))
