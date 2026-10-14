# Threat model

## Scope and protected state

A single configured sender signs a fictional invoice event. The receiver authenticates, checks age, validates JSON and business shape, and records a local SQLite effect. The protected assets are the shared key, event identity, local business state, and the truthfulness of completion results.

## Actors and capabilities

- Legitimate sender: can sign new messages and retry old ones.
- Observer: can capture and resend a signed request but cannot calculate a new valid signature.
- Modifying attacker: can change body or metadata but lacks the key.
- Faulty authorized sender: can sign conflicting content using an existing ID.
- Concurrent delivery workers: can race to process the same event.
- Interrupted application: can fail between claim and local commit.

## Control-to-evidence map

| Risk | Implemented control | Remaining boundary |
|---|---|---|
| Byte or metadata tampering | HMAC-SHA256 over a versioned, delimited envelope | Anyone with the key can sign |
| Old captured request | Authenticated timestamp, inclusive +/-300 seconds | Replays within the window remain fresh |
| Duplicate accepted event | Event primary key plus body digest | Scoped to one sender/database |
| Concurrent claims | BEGIN IMMEDIATE and one transaction | Local SQLite locking, not distributed coordination |
| Partial local update | Event and simulated effect share commit/rollback | Remote services are not in this transaction |
| Ambiguous JSON | UTF-8, object root, duplicate-key and non-finite-constant rejection | Business authorization remains separate |
| Invalid fictional payload | Exact type, invoice ID, integer amount constraints | Not a real invoice policy |

## Deliberate exclusions

No HTTP listener, TLS termination, key rotation, tenant system, rate limiting, secret vault, account authorization, remote queue, or provider adapter is supplied. A 64 KiB limit is not DoS protection. Records have no pruning policy and grow indefinitely. SQLite storage must have suitable local locking/durability behavior; this is not a network-filesystem recommendation.

The tests inject exceptions and reopen connections. They do not establish process-kill recovery, power-loss durability, or adversarial performance. A new event ID for the same invoice can create another simulated effect: event deduplication is not business uniqueness.

The custom signing contract is not RFC 9421. A provider-specific adapter must independently establish exact signed components, delivery semantics, timestamp units, ID scope, and retention requirements.
