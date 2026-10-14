"""Single-sender, offline reference protocol. Not a provider adapter."""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
import hashlib
import hmac
import json
import re
import sqlite3
import time
from pathlib import Path

MAX_BODY = 64 * 1024
ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
SIG = re.compile(r"[0-9a-f]{64}\Z")


class WebhookRejected(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code


def reject(code, detail):
    raise WebhookRejected(code, detail)


def _envelope(secret, timestamp, event_id, body):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Configure a bytes signing key of at least 32 bytes")
    if type(timestamp) is not int or not 0 <= timestamp <= 2**63 - 1:
        reject("invalid_timestamp", "timestamp must be nonnegative integer seconds")
    if not isinstance(event_id, str) or not ID.fullmatch(event_id):
        reject("invalid_event_id", "event_id must be 1-128 ASCII letters, digits, _ or -")
    if not isinstance(body, bytes):
        reject("invalid_body", "body must be exact bytes")
    if len(body) > MAX_BODY:
        reject("body_too_large", "body exceeds the 64 KiB teaching limit")
    return b"webhook-trust-v1\n" + str(timestamp).encode("ascii") + b"\n" + event_id.encode("ascii") + b"\n" + body


def signature_for(*, secret, timestamp, event_id, body):
    return hmac.new(secret, _envelope(secret, timestamp, event_id, body), hashlib.sha256).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject("invalid_json", "duplicate JSON keys are not allowed")
        result[key] = value
    return result


def _no_constant(value):
    reject("invalid_json", "non-finite JSON numbers are not allowed")


def _bounded_int(value):
    if len(value.lstrip('-')) > 128:
        reject("invalid_json", "JSON integers are limited to 128 digits")
    return int(value)


def _check_depth(payload):
    pending = [(payload, 1)]
    while pending:
        node, depth = pending.pop()
        if isinstance(node, (dict, list)):
            if depth > 32:
                reject("invalid_json", "JSON containers are limited to 32 levels")
            children = node.values() if isinstance(node, dict) else node
            pending.extend((child, depth + 1) for child in children)


@dataclass(frozen=True)
class VerifiedEvent:
    event_id: str
    timestamp: int
    body: bytes
    body_digest: str

    @property
    def payload(self):
        # Return a fresh object: callers cannot mutate the authenticated body.
        return json.loads(self.body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_no_constant, parse_int=_bounded_int)


def verify_webhook(*, secret, timestamp, event_id, body, signature, now=None, window=300):
    """Validate envelope, authenticate, check freshness, then parse; no state writes."""
    message = _envelope(secret, timestamp, event_id, body)
    if not isinstance(signature, str) or not SIG.fullmatch(signature):
        reject("invalid_signature", "signature must be 64 lowercase hex characters")
    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        reject("invalid_signature", "signature does not match the signed bytes")
    if now is None:
        now = int(time.time())
    if type(now) is not int or type(window) is not int or window < 0:
        raise ValueError("now and window must be integers; window must be nonnegative")
    if abs(now - timestamp) > window:
        reject("outside_window", "signed timestamp is outside the replay window")
    try:
        payload = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_no_constant, parse_int=_bounded_int)
        _check_depth(payload)
    except (ValueError, RecursionError) as exc:
        raise WebhookRejected("invalid_json", "body must be valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        reject("invalid_payload", "body must be a JSON object")
    return VerifiedEvent(event_id, timestamp, body, hashlib.sha256(body).hexdigest())


class SQLiteConsumer:
    """Atomically record an event and a LOCAL simulated effect in the same database.

    One database belongs to one authenticated sender. Retention is indefinite in
    this teaching implementation. No external network or financial action occurs.
    """
    def __init__(self, path: str | Path):
        self.path = str(path)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    digest TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status='completed')
                );
                CREATE TABLE IF NOT EXISTS effects (
                    event_id TEXT PRIMARY KEY REFERENCES events(event_id),
                    invoice_id TEXT NOT NULL,
                    amount INTEGER NOT NULL
                );
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _apply_effect(self, db, event, payload):
        db.execute("INSERT INTO effects VALUES (?, ?, ?)", (event.event_id, payload["invoice_id"], payload["amount"]))

    def receive(self, **request):
        event = verify_webhook(**request)
        payload = event.payload
        if (set(payload) != {"type", "invoice_id", "amount"}
            or payload["type"] != "invoice.paid"
            or not isinstance(payload["invoice_id"], str)
            or not ID.fullmatch(payload["invoice_id"])
            or type(payload["amount"]) is not int
            or not 0 < payload["amount"] <= 1_000_000):
            reject("invalid_business_payload", "expected invoice.paid, a valid invoice_id and integer amount 1..1000000")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT digest, status FROM events WHERE event_id=?", (event.event_id,)).fetchone()
            if existing:
                if existing[0] != event.body_digest:
                    reject("event_conflict", "event_id was already used with a different body")
                db.commit()
                return {"decision": "duplicate_completed", "effect_applied": False}
            db.execute("INSERT INTO events VALUES (?, ?, 'completed')", (event.event_id, event.body_digest))
            self._apply_effect(db, event, payload)
            db.commit()
            return {"decision": "completed", "effect_applied": True}
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def counts(self):
        with closing(self._connect()) as db:
            return {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("events", "effects")}
