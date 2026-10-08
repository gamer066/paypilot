"""PayPilot database (SQLite). One small file, no setup needed."""
import sqlite3
from datetime import datetime

DB_FILE = "paypilot.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY, customer TEXT, email TEXT, trn TEXT,
    amount_excl_vat REAL, vat REAL, total REAL,
    issue_date TEXT, due_date TEXT,
    state TEXT DEFAULT 'open',          -- open / paid / disputed
    promised_date TEXT, source TEXT, created TEXT, language TEXT DEFAULT 'en');
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, tone TEXT,
    subject TEXT, body TEXT,
    status TEXT,                        -- draft / pending_approval / approved / rejected / sent
    created TEXT, decided_by TEXT, decided_at TEXT, sent_at TEXT);
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, reason TEXT,
    status TEXT DEFAULT 'open', created TEXT, handled_at TEXT);
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT, text TEXT,
    intent TEXT, summary TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT, to_addr TEXT, subject TEXT,
    body TEXT, draft_id INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT,
    action TEXT, invoice_id TEXT, detail TEXT);
"""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn():
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row
    return c


def init():
    c = _conn()
    c.executescript(SCHEMA)
    try:  # older database files do not have the language column yet
        c.execute("ALTER TABLE invoices ADD COLUMN language TEXT DEFAULT 'en'")
    except sqlite3.OperationalError:
        pass
    c.commit()
    c.close()


def query(sql, args=()):
    c = _conn()
    try:
        return [dict(r) for r in c.execute(sql, args).fetchall()]
    finally:
        c.close()


def run(sql, args=()):
    c = _conn()
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid
    finally:
        c.close()


def log(actor, action, invoice_id="", detail=""):
    """Write one line to the audit log. Every action goes through here."""
    run("INSERT INTO audit (ts, actor, action, invoice_id, detail) VALUES (?,?,?,?,?)",
        (now(), actor, action, invoice_id, detail))


def upsert_invoice(inv, source="upload"):
    old = query("SELECT state, promised_date, language FROM invoices WHERE id=?", (inv["id"],))
    state = old[0]["state"] if old else "open"
    promised = old[0]["promised_date"] if old else None
    lang = inv.get("language") or (old[0]["language"] if old else "en") or "en"
    run("""INSERT OR REPLACE INTO invoices
           (id, customer, email, trn, amount_excl_vat, vat, total, issue_date,
            due_date, state, promised_date, source, created, language)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (inv["id"], inv.get("customer", ""), inv.get("email", ""), inv.get("trn", ""),
         inv.get("amount_excl_vat") or 0, inv.get("vat") or 0, inv.get("total") or 0,
         inv.get("issue_date", ""), inv.get("due_date", ""), state, promised, source, now(), lang))


def reset():
    c = _conn()
    c.executescript("DROP TABLE IF EXISTS invoices; DROP TABLE IF EXISTS drafts;"
                    "DROP TABLE IF EXISTS escalations; DROP TABLE IF EXISTS replies;"
                    "DROP TABLE IF EXISTS outbox; DROP TABLE IF EXISTS audit;")
    c.commit()
    c.close()
    init()
