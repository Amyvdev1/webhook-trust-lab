# Webhook Trust Lab

**A valid signature is not replay protection. A duplicate record is not proof of a completed action.**

An independent application-security case study by Amy V. Follow one fictional invoice event through authentication, freshness, duplicate detection, and a local transaction. No external service, credentials, or payment is used.

## Fresh-clone quickstart

Requires Python 3.11+ with SQLite and Git. No dependency installation, credentials, or network requests are needed after cloning. Use a **local, unsynchronized folder** because the tests exercise SQLite transactions. On Windows, for example, start in `$env:LOCALAPPDATA`; avoid OneDrive and network shares.

```sh
git clone https://github.com/Amyvdev1/webhook-trust-lab.git
cd webhook-trust-lab
python -m unittest -v
python demo.py --output output/scenarios.json
```

Use `python3` if your system names Python that way. Expect the test runner to finish with `OK`. The demo explains nine scenarios, including a valid replay accepted by the stateless verifier, a duplicate suppressed by the stateful consumer, and rollback without a committed local effect. Your new evidence is in `output/scenarios.json`; the checked-in evidence remains unchanged.

**Inspect the result:** open `site/index.html` in your browser. This explorer displays the bundled recorded evidence; it does not run Python or automatically reload your newly generated JSON. Compare it with your local output when verifying behavior.

**Try the key distinction:** compare “A signature is repeatable” with “Replay inside the window.” Authentication answers who signed these bytes. Stateful processing answers whether this event already completed locally. Neither is proof of an external payment.

If Python cannot import `sqlite3`, install a Python distribution with SQLite support. For database locking or permission errors, move the clone to a writable local folder and rerun; do not disable the concurrency tests. No service needs to be left running after the demo.

## Review in five minutes

1. Run `python -m unittest -v`.
2. Run `python demo.py --output output/scenarios.json` to generate fresh evidence without replacing the recorded sample.
3. Inspect [the nine recorded scenarios](evidence/scenarios.json).
4. Inspect [the threat model](docs/threat-model.md) and [claims and evidence](docs/claims-and-evidence.md).
5. Open `site/index.html` for the recorded-evidence explorer, or watch [the walkthrough with original music](media/walkthrough-with-music.mp4).

Requires Python 3.11+ with SQLite. The core lab uses the standard library only. The included evidence records the actual environment tested; support for other versions is not a claim they were executed locally.

## The experiment

The stateless verifier accepts the same authentic, fresh message twice. The SQLite consumer then demonstrates the missing stateful decision: an event already completed locally does not create another local effect. Conflicting content under the same event ID is rejected. Tests exercise simultaneous deliveries and rollback around the local effect.

```text
exact bytes + timestamp + event ID
                 |
       envelope validation
                 |
       HMAC authentication
                 |
         freshness window
                 |
      JSON + business schema
                 |
 SQLite transaction: event + local effect
                 |
     completed / duplicate / rejected
```

## Protocol choices

The signed bytes are `webhook-trust-v1\n{timestamp}\n{event_id}\n{raw_body}`. Timestamp is integer Unix seconds; IDs are 1-128 ASCII letters, digits, underscores, or hyphens. HMAC-SHA256 is encoded as 64 lowercase hexadecimal characters. The symmetric 300-second window includes both boundary values. The body limit is 64 KiB.

This is a custom teaching protocol, not RFC 9421 or a vendor's webhook format. `verify_webhook` authenticates before parsing JSON and does not write state. `SQLiteConsumer.receive` additionally validates the fictional invoice schema and atomically inserts the event and simulated effect in one database transaction.

JSON containers are limited to 32 levels and integers to 128 digits. Duplicate object keys and non-finite constants such as `NaN` are rejected. These are explicit teaching constraints; they do not establish resistance to sustained resource-exhaustion attacks.

## Boundaries that matter

- A database is scoped to one authenticated sender. Multi-tenant systems need authenticated sender namespaces and isolated secrets.
- The “effect” is an SQLite row, not a payment, email, or remote request. Remote side effects require a different recovery/idempotency design.
- Records are retained indefinitely. Retention, cleanup, secret rotation, transport authentication, authorization, rate limits, and deployment are not implemented.
- A new event ID can describe the same invoice. Event-ID deduplication does not replace business uniqueness rules.
- Filesystem and SQLite durability assumptions still apply. Run on a local filesystem; this is not a distributed store or a deployment recommendation for synchronized/network folders.
- No live provider compatibility, penetration test, throughput benchmark, or novel vulnerability is claimed.

## Provenance

This is a new implementation created after reviewing a supplied draft whose original Python source was unavailable. It does not inherit that draft's claimed test result. See `evidence/verification.json` and `evidence/test-output.txt` for this version's verification.

The work is an independent portfolio sample, not commissioned by or affiliated with Cracken. See [GitHub Actions](https://github.com/Amyvdev1/webhook-trust-lab/actions/workflows/verify.yml) for the current hosted verification status.

## Files

- `webhook_security.py`: protocol verification and transactional local consumer.
- `test_webhook_security.py`: deterministic verification, persistence, failure, and concurrency tests.
- `demo.py`: nine reproducible evidence scenarios.
- `docs/`: threat model, claims, and verification record.
- `media/`: actual local browser walkthrough and verification.

## Sources

- [OWASP Webhook Security](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html)
- [Python hmac](https://docs.python.org/3/library/hmac.html)
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html)
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html)
- [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421.html)

MIT License. Copyright 2026 Amy V.

## Watch and explore

[Portfolio case study](https://amy-villa-signal-gallery.vercel.app/projects/webhook-trust-lab) · [Recorded-evidence explorer](https://amy-villa-signal-gallery.vercel.app/project-media/webhook-trust-lab/site/index.html)

The walkthrough records the local evidence explorer. The original instrumental score uses synthesized tones, no sampled recordings, and is included under this repository’s MIT license. There is no voiceover or burned-in subtitle track.
