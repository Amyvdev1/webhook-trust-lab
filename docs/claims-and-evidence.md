# Claims and evidence

Claims below refer only to this implementation. Exact source hashes and execution environment are in `evidence/verification.json`.

| Claim | Evidence | Classification |
|---|---|---|
| Exact body and signed metadata are authenticated | protocol vector, body/timestamp/ID/serialization tests | Executed local tests |
| Signature rejection occurs before JSON parsing | parser-spy test | Executed local test |
| Authentic old/future messages fail freshness | tests re-sign each altered timestamp | Executed local tests |
| Fresh authentic delivery can pass twice | stateless replay test and demo scenario 1 | Observed local behavior |
| Duplicate completion adds no second local effect | persistence duplicate and resigned-retry tests | Executed local tests |
| Simultaneous deliveries create one local effect | 16 deliveries, 8 threads, separate connections | Local concurrency check |
| Exceptions before commit roll back both writes | before-effect and after-effect injections | Local fault injection |
| State survives reopening the consumer | reopened database test | Local connection lifecycle check |
| Entire receiver is constant-time | No such claim | Not established |
| Live vendor interoperability or production adoption | No such claim | Not evaluated |
| Exactly-once remote side effects | No such claim | Outside transaction boundary |
| Professional employment, commission, or external security review | No such claim | Independent portfolio work |

Using `hmac.compare_digest` is an inspected code choice supported by Python's documentation; it is not an empirical timing audit. The supplied historical test total is superseded only for this new implementation, not retroactively corrected as an executed historical result.
