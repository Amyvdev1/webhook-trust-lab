"""Generate fresh, deterministic local evidence; never contacts a provider."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from webhook_security import SQLiteConsumer, WebhookRejected, signature_for, verify_webhook

KEY = b"local-fixture-only-not-a-real-key!"
NOW = 1_700_000_000
BODY = b'{"type":"invoice.paid","invoice_id":"inv_7","amount":50}'

def request(body=BODY, event_id="evt_1", timestamp=NOW):
    return dict(secret=KEY, timestamp=timestamp, event_id=event_id, body=body, now=NOW,
                signature=signature_for(secret=KEY, timestamp=timestamp, event_id=event_id, body=body))

def run():
    records = []
    def record(title, action, meaning):
        try:
            outcome = action()
        except WebhookRejected as exc:
            outcome = {"decision": "rejected", "reason": exc.code}
        records.append(dict(title=title, outcome=outcome, meaning=meaning))
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        db = Path(directory) / "demo.sqlite"
        consumer = SQLiteConsumer(db)
        record("A signature is repeatable", lambda: {"signature_checks_passed": sum(verify_webhook(**request()) is not None for _ in range(2)), "deliveries": 2}, "The same signed bytes authenticate twice. The stateless verifier does not deduplicate.")
        record("First delivery", lambda: consumer.receive(**request()), "The event record and the local simulated effect commit together.")
        record("Replay inside the window", lambda: consumer.receive(**request()), "A completed event is recognized. No second local effect is inserted.")
        record("Authentic but stale", lambda: consumer.receive(**request(timestamp=NOW-301)), "The signature was recalculated for the old timestamp. Freshness is the failing control.")
        record("Changed bytes", lambda: consumer.receive(**{**request(), "body": BODY.replace(b"50", b"500")}), "A changed body with the original signature cannot pass authentication.")
        record("Same identity, new content", lambda: consumer.receive(**request(body=BODY.replace(b"50", b"60"))), "Even a valid signature does not authorize reuse of an existing event identity with different content.")
        record("Reopen the database", lambda: SQLiteConsumer(db).receive(**request()), "Duplicate state survives closing and reopening the consumer.")
        parallel = SQLiteConsumer(Path(directory) / "parallel.sqlite")
        def simultaneous():
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                outcomes = list(pool.map(lambda _: parallel.receive(**request()), range(16)))
            return {"deliveries": 16, "effects_applied": sum(r["effect_applied"] for r in outcomes), **parallel.counts()}
        record("Sixteen simultaneous deliveries", simultaneous, "Independent SQLite connections serialize claims. This is a local concurrency check, not a load benchmark.")
        recovery = SQLiteConsumer(Path(directory) / "recovery.sqlite")
        def recover():
            with patch.object(recovery, "_apply_effect", side_effect=RuntimeError("injected failure")):
                try:
                    recovery.receive(**request())
                except RuntimeError:
                    pass
            before = recovery.counts()
            result = recovery.receive(**request())
            return {"after_rollback": before, "retry": result, "after_retry": recovery.counts()}
        record("Failure, rollback, retry", recover, "An injected exception rolls back the local transaction. A later attempt can complete. External services are outside this transaction.")
    return {"schema_version": 1, "mode": "offline_deterministic_reference", "clock": NOW, "provider_calls": 0,
            "scope": "One sender; SQLite-local simulated effect; no external payment", "scenarios": records}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
