const EVIDENCE = {
  "schema_version": 1,
  "mode": "offline_deterministic_reference",
  "clock": 1700000000,
  "provider_calls": 0,
  "scope": "One sender; SQLite-local simulated effect; no external payment",
  "scenarios": [
    {
      "title": "A signature is repeatable",
      "outcome": {
        "signature_checks_passed": 2,
        "deliveries": 2
      },
      "meaning": "The same signed bytes authenticate twice. The stateless verifier does not deduplicate."
    },
    {
      "title": "First delivery",
      "outcome": {
        "decision": "completed",
        "effect_applied": true
      },
      "meaning": "The event record and the local simulated effect commit together."
    },
    {
      "title": "Replay inside the window",
      "outcome": {
        "decision": "duplicate_completed",
        "effect_applied": false
      },
      "meaning": "A completed event is recognized. No second local effect is inserted."
    },
    {
      "title": "Authentic but stale",
      "outcome": {
        "decision": "rejected",
        "reason": "outside_window"
      },
      "meaning": "The signature was recalculated for the old timestamp. Freshness is the failing control."
    },
    {
      "title": "Changed bytes",
      "outcome": {
        "decision": "rejected",
        "reason": "invalid_signature"
      },
      "meaning": "A changed body with the original signature cannot pass authentication."
    },
    {
      "title": "Same identity, new content",
      "outcome": {
        "decision": "rejected",
        "reason": "event_conflict"
      },
      "meaning": "Even a valid signature does not authorize reuse of an existing event identity with different content."
    },
    {
      "title": "Reopen the database",
      "outcome": {
        "decision": "duplicate_completed",
        "effect_applied": false
      },
      "meaning": "Duplicate state survives closing and reopening the consumer."
    },
    {
      "title": "Sixteen simultaneous deliveries",
      "outcome": {
        "deliveries": 16,
        "effects_applied": 1,
        "events": 1,
        "effects": 1
      },
      "meaning": "Independent SQLite connections serialize claims. This is a local concurrency check, not a load benchmark."
    },
    {
      "title": "Failure, rollback, retry",
      "outcome": {
        "after_rollback": {
          "events": 0,
          "effects": 0
        },
        "retry": {
          "decision": "completed",
          "effect_applied": true
        },
        "after_retry": {
          "events": 1,
          "effects": 1
        }
      },
      "meaning": "An injected exception rolls back the local transaction. A later attempt can complete. External services are outside this transaction."
    }
  ]
};
const VERIFICATION = {
  "verified_at": "2026-10-14T15:40:08.384758+00:00",
  "python": "3.14.3",
  "platform": "Windows",
  "tests": 39,
  "failures": 0,
  "errors": 0,
  "skipped": 0,
  "provider_calls": 0,
  "github_actions": {
    "status_at_local_verification": "configured, not run",
    "subsequent_verification": {
      "conclusion": "success",
      "workflow": "Verify reference lab",
      "run_id": 38595723539,
      "run_updated_at": "2026-10-14T16:10:20Z",
      "checked_at": "2026-10-14T16:39:14.906923+00:00",
      "head_sha": "c5f390a948c4ef94a26fdc18ae0ec7018db0c2db",
      "url": "https://github.com/Amyvdev1/webhook-trust-lab/actions/runs/38595723539",
      "matrix": [
        "ubuntu-latest / Python 3.11",
        "ubuntu-latest / Python 3.14",
        "windows-latest / Python 3.11",
        "windows-latest / Python 3.14"
      ],
      "note": "All four jobs passed. This dated hosted result supplements the original local observation; it is not a continuously refreshed status."
    }
  },
  "command": "python -m unittest -v",
  "source_sha256": {
    "webhook_security.py": "f68bba507bca93cb96d63caacaf0df76f04fab4fa0c10fb5a494d7ff7536a196",
    "test_webhook_security.py": "665b05f38596bda9c3b78330a9d38bf4963f1da60867dfad535d68d6f7447b93",
    "demo.py": "55da261c68d49d0b7e2aa57c3b1ca01a1d02ff642b9df7cb21f9e9fe436eb281"
  }
};
