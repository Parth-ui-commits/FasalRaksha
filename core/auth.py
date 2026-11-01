"""Mobile number + password accounts. Passwords are salted PBKDF2-SHA256 hashes, never stored in plain text.
Sign-in by SMS OTP needs a paid SMS service, so it is left as a roadmap item."""
import hashlib, hmac, os, re, secrets
from datetime import datetime, timedelta
from . import db

SESSION_DAYS = 7


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 200_000)


def valid_mobile(m):
    return bool(re.fullmatch(r"[6-9]\d{9}", m or ""))


def register(mobile, name, pw, lang="en", state=""):
    """Returns (user_dict or None, error_code or None)."""
    mobile, name = (mobile or "").strip(), (name or "").strip()
    if not valid_mobile(mobile):
        return None, "bad_mobile"
    if len(name) < 2:
        return None, "bad_name"
    if len(pw or "") < 6:
        return None, "short_pw"
    if db.query("SELECT id FROM users WHERE mobile=?", (mobile,), one=True):
        return None, "exists"
    salt = os.urandom(16)
    uid = db.execute("INSERT INTO users(mobile,name,salt,pw_hash,lang,state,created_at) VALUES(?,?,?,?,?,?,?)",
                     (mobile, name, salt, _hash(pw, salt), lang, state, datetime.utcnow().isoformat(timespec="seconds")))
    return get_user(uid), None


def login(mobile, pw):
    u = db.query("SELECT * FROM users WHERE mobile=?", ((mobile or "").strip(),), one=True)
    if not u or not hmac.compare_digest(_hash(pw or "", u["salt"]), u["pw_hash"]):
        return None
    return _public(u)


def _public(u):
    return {k: u[k] for k in ("id", "mobile", "name", "lang", "state")}


def get_user(uid):
    u = db.query("SELECT * FROM users WHERE id=?", (uid,), one=True)
    return _public(u) if u else None


def set_lang(uid, lang):
    db.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))


def make_session(uid):
    token = secrets.token_urlsafe(24)
    exp = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    db.execute("INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)", (token, uid, exp))
    return token


def user_from_token(token):
    if not token:
        return None
    s = db.query("SELECT * FROM sessions WHERE token=?", (token,), one=True)
    if not s or s["expires"] < datetime.utcnow().isoformat(timespec="seconds"):
        return None
    return get_user(s["user_id"])


def end_session(token):
    db.execute("DELETE FROM sessions WHERE token=?", (token,))
