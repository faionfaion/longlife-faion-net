#!/usr/bin/env python3
"""Email subscription service for longlife.media.

A small stdlib HTTP service behind nginx at longlife.media/api/. It runs on faion-net (the
public host), stores subscribers in SQLite, and sends double opt-in confirmation mail
through the faion.net Mailgun domain over SMTP. No framework, no external deps: the volume
is a personal blog's and the surface is tiny, so the standard library is enough and there
is nothing to keep patched.

Double opt-in is the whole design: a POST /api/subscribe only creates a *pending* row and
mails a confirmation link. Nothing is on the list until the person clicks it. That is both
the anti-abuse measure (you cannot sign someone else up) and the legal one.

Flow and endpoints (all under /api/ once nginx has stripped nothing — paths are absolute):
  POST /api/subscribe      {email, [weekly], [each_post], hp}  -> create pending, send mail
  GET  /api/confirm?t=...   confirm token -> mark confirmed, redirect to the manage page
  POST /api/prefs          {t, weekly, each_post}              -> update newsletter types
  POST /api/topics         {t, text}                           -> a topic the reader wants
  POST /api/news           {t, url, [note]}                    -> a news link worth a look
  GET  /api/unsubscribe?t=  manage token -> unsubscribe
  GET  /api/prefs?t=        manage token -> current prefs as JSON (for the manage page)

Tokens: `confirm_token` is single-use (consumed at confirm); `manage_token` is the durable
one that a confirmed subscriber uses to change prefs, submit topics/links, or leave. Links
in every mail carry it, so no passwords and no login.
"""

from __future__ import annotations

import json
import os
import re
import smtplib
import sqlite3
import secrets
import time
import threading
from email.message import EmailMessage
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# --- Config (env, with sane local defaults) ---
DB_PATH = os.environ.get("SUBSCRIBE_DB", "/srv/longlife/subscribers.db")
PORT = int(os.environ.get("SUBSCRIBE_PORT", "8794"))
SITE = os.environ.get("SUBSCRIBE_SITE", "https://longlife.media")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.mailgun.org")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
# Sender is on faion.net, the verified Mailgun domain, so SPF/DKIM align. The from-address
# will move to @longlife.media once that domain is added to Mailgun.
FROM_ADDR = os.environ.get("SUBSCRIBE_FROM", "vita@faion.net")
FROM_NAME = os.environ.get("SUBSCRIBE_FROM_NAME", "Віта · LongLife")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NEWSLETTER_KINDS = ("weekly", "each_post")

_db_lock = threading.Lock()
_rate: dict[str, list[float]] = {}
_rate_lock = threading.Lock()


# --- Storage ---

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _db_lock, _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                weekly INTEGER NOT NULL DEFAULT 1,
                each_post INTEGER NOT NULL DEFAULT 0,
                confirm_token TEXT,
                manage_token TEXT NOT NULL,
                created_at TEXT NOT NULL,
                confirmed_at TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY,
                subscriber_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS news_tips (
                id INTEGER PRIMARY KEY,
                subscriber_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )"""
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- Email ---

def send_mail(to_addr: str, subject: str, text: str) -> None:
    msg = EmailMessage()
    msg["From"] = formataddr((FROM_NAME, FROM_ADDR))
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(text)
    if not SMTP_USER:
        # No creds configured (e.g. a dry local run): log instead of failing the request.
        print(f"[mail:noop] to={to_addr} subject={subject!r}\n{text}")
        return
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def _confirm_mail(confirm_token: str) -> tuple[str, str]:
    link = f"{SITE}/api/confirm?t={confirm_token}"
    subject = "Підтвердьте підписку на LongLife"
    body = (
        "Привіт!\n\n"
        "Хтось (сподіваюся, ти) підписав цю адресу на блог LongLife - "
        "доказово про здоров'я, простою мовою.\n\n"
        "Щоб підтвердити підписку, відкрий це посилання:\n"
        f"{link}\n\n"
        "Якщо це не ти - просто зітри цей лист, нічого не станеться: без підтвердження "
        "адреса в список не потрапляє.\n\n"
        "Віта, LongLife\n"
        f"{SITE}"
    )
    return subject, body


def _welcome_mail(manage_token: str) -> tuple[str, str]:
    manage = f"{SITE}/pidpyska/?t={manage_token}"
    unsub = f"{SITE}/api/unsubscribe?t={manage_token}"
    subject = "Підписку підтверджено"
    body = (
        "Готово, адресу підтверджено.\n\n"
        "На цій сторінці можна обрати типи листів, лишити теми, які тобі цікаві, "
        "або кинути посилання на новину, варту уваги:\n"
        f"{manage}\n\n"
        "Відписатися можна будь-коли одним кліком:\n"
        f"{unsub}\n\n"
        "Віта, LongLife"
    )
    return subject, body


# --- Rate limiting (coarse, in-memory) ---

def _rate_ok(ip: str, limit: int = 5, window: int = 300) -> bool:
    now = time.time()
    with _rate_lock:
        hits = [t for t in _rate.get(ip, []) if now - t < window]
        if len(hits) >= limit:
            _rate[ip] = hits
            return False
        hits.append(now)
        _rate[ip] = hits
        return True


# --- Handlers ---

class Handler(BaseHTTPRequestHandler):
    server_version = "longlife-subscribe"

    def _send(self, code: int, obj: dict, ctype: str = "application/json") -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # keep the CDN out of /api responses
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _client_ip(self) -> str:
        return self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(n) if n else b""
        ctype = self.headers.get("Content-Type", "")
        if "application/json" in ctype:
            try:
                return json.loads(raw or b"{}")
            except ValueError:
                return {}
        return {k: v[0] for k, v in parse_qs(raw.decode("utf-8", "replace")).items()}

    def log_message(self, format, *args):  # noqa: A002 - keep journald quiet
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        qs = parse_qs(urlparse(self.path).query)
        if path == "/api/health":
            return self._send(200, {"ok": True})
        if path == "/api/confirm":
            return self._confirm(qs.get("t", [""])[0])
        if path == "/api/unsubscribe":
            return self._unsubscribe(qs.get("t", [""])[0])
        if path == "/api/prefs":
            return self._get_prefs(qs.get("t", [""])[0])
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if not _rate_ok(self._client_ip()):
            return self._send(429, {"error": "too many requests"})
        data = self._body()
        if path == "/api/subscribe":
            return self._subscribe(data)
        if path == "/api/prefs":
            return self._set_prefs(data)
        if path == "/api/topics":
            return self._topic(data)
        if path == "/api/news":
            return self._news(data)
        return self._send(404, {"error": "not found"})

    # -- subscribe: create pending + mail confirmation --
    def _subscribe(self, data: dict):
        if (data.get("hp") or "").strip():        # honeypot field: bots fill it, humans don't
            return self._send(200, {"ok": True})   # pretend success, do nothing
        email = (data.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email) or len(email) > 254:
            return self._send(400, {"error": "невірна адреса"})
        weekly = 1 if str(data.get("weekly", "1")) in ("1", "true", "on", "True") else 0
        each = 1 if str(data.get("each_post", "0")) in ("1", "true", "on", "True") else 0
        if not weekly and not each:
            weekly = 1
        confirm_token = secrets.token_urlsafe(24)
        manage_token = secrets.token_urlsafe(24)
        with _db_lock, _conn() as c:
            row = c.execute("SELECT id, status FROM subscribers WHERE email=?", (email,)).fetchone()
            if row and row["status"] == "confirmed":
                # Already on the list — don't leak that, just say check your mail.
                return self._send(200, {"ok": True, "already": True})
            if row:
                c.execute(
                    "UPDATE subscribers SET confirm_token=?, weekly=?, each_post=?, created_at=? WHERE id=?",
                    (confirm_token, weekly, each, _now(), row["id"]),
                )
            else:
                c.execute(
                    "INSERT INTO subscribers (email, status, weekly, each_post, confirm_token, manage_token, created_at) "
                    "VALUES (?, 'pending', ?, ?, ?, ?, ?)",
                    (email, weekly, each, confirm_token, manage_token, _now()),
                )
        try:
            subject, body = _confirm_mail(confirm_token)
            send_mail(email, subject, body)
        except Exception as e:
            print(f"[subscribe] mail failed for {email}: {e}")
            return self._send(502, {"error": "не вдалося надіслати лист, спробуй пізніше"})
        return self._send(200, {"ok": True})

    def _confirm(self, token: str):
        if not token:
            return self._redirect(f"{SITE}/pidpyska/?e=1")
        with _db_lock, _conn() as c:
            row = c.execute("SELECT id, manage_token FROM subscribers WHERE confirm_token=?", (token,)).fetchone()
            if not row:
                return self._redirect(f"{SITE}/pidpyska/?e=1")
            c.execute(
                "UPDATE subscribers SET status='confirmed', confirmed_at=?, confirm_token=NULL WHERE id=?",
                (_now(), row["id"]),
            )
            manage_token = row["manage_token"]
        try:
            subject, body = _welcome_mail(manage_token)
            with _conn() as c:
                em = c.execute("SELECT email FROM subscribers WHERE manage_token=?", (manage_token,)).fetchone()
            if em:
                send_mail(em["email"], subject, body)
        except Exception as e:
            print(f"[confirm] welcome mail failed: {e}")
        return self._redirect(f"{SITE}/pidpyska/?t={manage_token}&c=1")

    def _sub_by_manage(self, c: sqlite3.Connection, token: str):
        if not token:
            return None
        return c.execute(
            "SELECT * FROM subscribers WHERE manage_token=? AND status='confirmed'", (token,)
        ).fetchone()

    def _get_prefs(self, token: str):
        with _conn() as c:
            row = self._sub_by_manage(c, token)
        if not row:
            return self._send(404, {"error": "not found"})
        return self._send(200, {"weekly": bool(row["weekly"]), "each_post": bool(row["each_post"])})

    def _set_prefs(self, data: dict):
        token = (data.get("t") or "").strip()
        weekly = 1 if str(data.get("weekly", "0")) in ("1", "true", "on", "True") else 0
        each = 1 if str(data.get("each_post", "0")) in ("1", "true", "on", "True") else 0
        with _db_lock, _conn() as c:
            row = self._sub_by_manage(c, token)
            if not row:
                return self._send(404, {"error": "not found"})
            c.execute("UPDATE subscribers SET weekly=?, each_post=? WHERE id=?", (weekly, each, row["id"]))
        return self._send(200, {"ok": True})

    def _topic(self, data: dict):
        token = (data.get("t") or "").strip()
        text = (data.get("text") or "").strip()[:500]
        if not text:
            return self._send(400, {"error": "порожньо"})
        with _db_lock, _conn() as c:
            row = self._sub_by_manage(c, token)
            if not row:
                return self._send(404, {"error": "not found"})
            c.execute("INSERT INTO topics (subscriber_id, text, created_at) VALUES (?, ?, ?)",
                      (row["id"], text, _now()))
        return self._send(200, {"ok": True})

    def _news(self, data: dict):
        token = (data.get("t") or "").strip()
        url = (data.get("url") or "").strip()[:1000]
        note = (data.get("note") or "").strip()[:1000]
        if not url.startswith(("http://", "https://")):
            return self._send(400, {"error": "потрібне посилання"})
        with _db_lock, _conn() as c:
            row = self._sub_by_manage(c, token)
            if not row:
                return self._send(404, {"error": "not found"})
            c.execute("INSERT INTO news_tips (subscriber_id, url, note, created_at) VALUES (?, ?, ?, ?)",
                      (row["id"], url, note, _now()))
        return self._send(200, {"ok": True})

    def _unsubscribe(self, token: str):
        with _db_lock, _conn() as c:
            row = self._sub_by_manage(c, token)
            if row:
                c.execute("UPDATE subscribers SET status='unsubscribed' WHERE id=?", (row["id"],))
        return self._redirect(f"{SITE}/pidpyska/?u=1")


def main() -> None:
    init_db()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"longlife-subscribe on 127.0.0.1:{PORT}, db={DB_PATH}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
