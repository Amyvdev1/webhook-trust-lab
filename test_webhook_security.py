import concurrent.futures
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from webhook_security import MAX_BODY, SQLiteConsumer, WebhookRejected, signature_for, verify_webhook

SECRET = b"local-fixture-only-not-a-real-key!"
NOW = 1_700_000_000
BODY = b'{"type":"invoice.paid","invoice_id":"inv_7","amount":50}'


def signed(body=BODY, event_id="evt_1", timestamp=NOW):
    return dict(secret=SECRET, timestamp=timestamp, event_id=event_id, body=body, now=NOW,
                signature=signature_for(secret=SECRET, timestamp=timestamp, event_id=event_id, body=body))


class VerificationTests(unittest.TestCase):
    def rejects(self, code, **request):
        with self.assertRaises(WebhookRejected) as caught:
            verify_webhook(**request)
        self.assertEqual(code, caught.exception.code)

    def test_valid_delivery(self):
        self.assertEqual(verify_webhook(**signed()).payload["amount"], 50)

    def test_protocol_vector_independent_envelope(self):
        expected = hmac.new(SECRET, b"webhook-trust-v1\n1700000000\nevt_1\n" + BODY, hashlib.sha256).hexdigest()
        self.assertEqual(expected, signed()["signature"])

    def test_body_tampering(self):
        self.rejects("invalid_signature", **{**signed(), "body": BODY.replace(b"50", b"51")})

    def test_timestamp_tampering(self):
        self.rejects("invalid_signature", **{**signed(), "timestamp": NOW + 1})

    def test_event_id_tampering(self):
        self.rejects("invalid_signature", **{**signed(), "event_id": "evt_2"})

    def test_validly_signed_stale_message(self):
        self.rejects("outside_window", **signed(timestamp=NOW - 301))

    def test_validly_signed_future_message(self):
        self.rejects("outside_window", **signed(timestamp=NOW + 301))

    def test_both_window_boundaries_are_inclusive(self):
        for delta in (-300, 300):
            with self.subTest(delta=delta):
                verify_webhook(**signed(timestamp=NOW + delta))

    def test_exact_byte_whitespace_changes(self):
        self.rejects("invalid_signature", **{**signed(), "body": BODY + b" "})

    def test_exact_byte_key_order_changes(self):
        body = b'{"amount":50,"invoice_id":"inv_7","type":"invoice.paid"}'
        self.rejects("invalid_signature", **{**signed(), "body": body})

    def test_signature_checked_before_json_parser(self):
        req = {**signed(), "body": b"not-json"}
        with patch("webhook_security.json.loads", side_effect=AssertionError("parser invoked")):
            self.rejects("invalid_signature", **req)

    def test_invalid_signature_format(self):
        for value in (None, b"00", "x" * 64, "0" * 63, "A" * 64):
            with self.subTest(value=value):
                self.rejects("invalid_signature", **{**signed(), "signature": value})

    def test_invalid_timestamp_types(self):
        for value in (True, 1.5, "1700000000", -1, 2**63):
            with self.subTest(value=value):
                self.rejects("invalid_timestamp", **{**signed(), "timestamp": value})

    def test_invalid_ids(self):
        for value in ("", "a\nb", "a.b", "a" * 129, None, "é"):
            with self.subTest(value=value):
                self.rejects("invalid_event_id", **{**signed(), "event_id": value})

    def test_body_limit_precedes_hmac(self):
        with patch("webhook_security.hmac.new", side_effect=AssertionError("HMAC invoked")):
            self.rejects("body_too_large", **{**signed_request_without_signing(), "body": b"x" * (MAX_BODY + 1)})

    def test_body_must_be_bytes(self):
        self.rejects("invalid_body", **{**signed(), "body": "{}"})

    def test_malformed_json(self):
        self.rejects("invalid_json", **signed(body=b"not-json"))

    def test_invalid_utf8(self):
        self.rejects("invalid_json", **signed(body=b'\xff'))

    def test_non_object_json(self):
        for body in (b"[]", b"null", b"50", b'"text"'):
            with self.subTest(body=body):
                self.rejects("invalid_payload", **signed(body=body))

    def test_duplicate_json_keys(self):
        self.rejects("invalid_json", **signed(body=b'{"amount":1,"amount":2}'))

    def test_nonfinite_json(self):
        self.rejects("invalid_json", **signed(body=b'{"amount":NaN}'))

    def test_oversized_integer_json_fails_with_structured_reason(self):
        self.rejects("invalid_json", **signed(body=b'{"amount":' + b'9' * 5000 + b'}'))

    def test_excessive_json_nesting_fails_with_structured_reason(self):
        self.rejects("invalid_json", **signed(body=b'{"value":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}'))

    def test_wrong_shared_key(self):
        self.rejects("invalid_signature", **{**signed(), "secret": b'wrong-fixture-key-not-a-secret!!!'})

    def test_empty_key_is_configuration_error(self):
        with self.assertRaises(ValueError):
            verify_webhook(**{**signed(), "secret": b""})

    def test_invalid_clock_configuration(self):
        for change in ({"now": True}, {"window": -1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_webhook(**{**signed(), **change})

    def test_signature_alone_accepts_replayed_bytes(self):
        request = signed()
        for _ in range(2):
            self.assertTrue(hmac.compare_digest(request["signature"], signature_for(**{k: request[k] for k in ("secret", "timestamp", "event_id", "body")})))

    def test_freshness_alone_does_not_deduplicate(self):
        self.assertEqual(verify_webhook(**signed()), verify_webhook(**signed()))


def signed_request_without_signing():
    return dict(secret=SECRET, timestamp=NOW, event_id="evt_1", body=BODY, signature="0" * 64, now=NOW)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "events.sqlite"
        self.consumer = SQLiteConsumer(self.path)

    def test_first_delivery_and_duplicate(self):
        self.assertEqual(self.consumer.receive(**signed())["decision"], "completed")
        self.assertEqual(self.consumer.receive(**signed())["decision"], "duplicate_completed")
        self.assertEqual(self.consumer.counts(), {"events": 1, "effects": 1})

    def test_resigned_retry_same_event(self):
        self.consumer.receive(**signed())
        self.assertFalse(self.consumer.receive(**signed(timestamp=NOW + 1))["effect_applied"])

    def test_conflict_preserves_original(self):
        self.consumer.receive(**signed())
        with self.assertRaises(WebhookRejected) as caught:
            self.consumer.receive(**signed(body=BODY.replace(b"50", b"60")))
        self.assertEqual(caught.exception.code, "event_conflict")
        self.assertEqual(self.consumer.counts(), {"events": 1, "effects": 1})

    def test_new_event_is_independent(self):
        self.consumer.receive(**signed())
        self.consumer.receive(**signed(event_id="evt_2"))
        self.assertEqual(self.consumer.counts()["effects"], 2)

    def test_reopening_database_retains_dedup(self):
        self.consumer.receive(**signed())
        other = SQLiteConsumer(self.path)
        self.assertFalse(other.receive(**signed())["effect_applied"])

    def test_invalid_json_does_not_poison_event_id(self):
        with self.assertRaises(WebhookRejected):
            self.consumer.receive(**signed(body=b"{"))
        self.assertEqual(self.consumer.counts()["events"], 0)
        self.assertTrue(self.consumer.receive(**signed())["effect_applied"])

    def test_business_schema_rejection_without_write(self):
        for body in (b"{}", BODY.replace(b"50", b"true"), BODY.replace(b"50", b"-1"), BODY.replace(b"invoice.paid", b"invoice.deleted")):
            with self.subTest(body=body), self.assertRaises(WebhookRejected):
                self.consumer.receive(**signed(body=body))
        self.assertEqual(self.consumer.counts(), {"events": 0, "effects": 0})

    def test_failure_after_claim_rolls_back_then_retry_succeeds(self):
        with patch.object(self.consumer, "_apply_effect", side_effect=RuntimeError("simulated failure")):
            with self.assertRaises(RuntimeError):
                self.consumer.receive(**signed())
        self.assertEqual(self.consumer.counts(), {"events": 0, "effects": 0})
        self.assertTrue(self.consumer.receive(**signed())["effect_applied"])

    def test_failure_after_local_effect_rolls_back_both(self):
        original = self.consumer._apply_effect
        def fail_after_effect(db, event, payload):
            original(db, event, payload)
            raise RuntimeError("failure before commit")
        with patch.object(self.consumer, "_apply_effect", side_effect=fail_after_effect):
            with self.assertRaises(RuntimeError):
                self.consumer.receive(**signed())
        self.assertEqual(self.consumer.counts(), {"events": 0, "effects": 0})

    def test_simultaneous_deliveries_apply_one_local_effect(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.consumer.receive(**signed()), range(16)))
        self.assertEqual(sum(r["effect_applied"] for r in results), 1)
        self.assertEqual(self.consumer.counts()["effects"], 1)

    def test_simultaneous_conflicting_claims_preserve_one_winner(self):
        requests = [signed(), signed(body=BODY.replace(b"50", b"60"))]
        def consume(req):
            try:
                return self.consumer.receive(**req)["decision"]
            except WebhookRejected as exc:
                return exc.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(consume, requests))
        self.assertCountEqual(outcomes, ["completed", "event_conflict"])
        self.assertEqual(self.consumer.counts(), {"events": 1, "effects": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
