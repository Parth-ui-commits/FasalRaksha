"""SQLite storage: users, sessions, fields, activity logs, sales, scans, price history.
SQLite is a single local file, free, and fine for a prototype. For many users, move to Postgres (for example a free Supabase or Neon tier)."""
import os, sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(os.getenv("FASAL_DB_PATH", Path(__file__).resolve().parent.parent / "data" / "fasalraksha.db"))
_ready = set()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, mobile TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  salt BLOB, pw_hash BLOB, lang TEXT DEFAULT 'en', state TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER, expires TEXT);
CREATE TABLE IF NOT EXISTS fields(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT, place TEXT, state TEXT,
  district TEXT, lat REAL, lon REAL, crop TEXT, area_acre REAL, sowing_date TEXT, soil_type TEXT, irrigation TEXT,
  exp_yield_qtl_acre REAL, status TEXT DEFAULT 'growing', created_at TEXT);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, field_id INTEGER, date TEXT, kind TEXT, note TEXT, cost_rs REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, field_id INTEGER, date TEXT, qty_qtl REAL, price_rs_qtl REAL, buyer TEXT);
CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY, field_id INTEGER, created_at TEXT, image_path TEXT, crop TEXT,
  label TEXT, confidence REAL, model TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS prices(date TEXT, state TEXT, commodity TEXT, market TEXT, district TEXT, modal REAL,
  PRIMARY KEY(date, commodity, market, district));
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    if str(DB_PATH) not in _ready:
        c.executescript(SCHEMA)
        _ready.add(str(DB_PATH))
    return c


def query(sql, args=(), one=False):
    with closing(connect()) as c:
        rows = [dict(r) for r in c.execute(sql, args).fetchall()]
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    with closing(connect()) as c:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid


def executemany(sql, seq):
    with closing(connect()) as c:
        c.executemany(sql, seq)
        c.commit()
