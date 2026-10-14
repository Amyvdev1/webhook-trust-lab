# Verification record

Verified locally: 2026-10-14T15:40:08.384758+00:00. Python 3.14.3; Windows.

39 tests passed; zero failures, errors, or skips. Nine deterministic demo scenarios were executed. Commands: `python -m unittest -v` and `python demo.py`.

The first sandbox attempt could not open SQLite files in the redirected system temporary directory. Tests now use isolated temporary directories beside the test file; explicit connection closing also avoids Windows file-handle leakage. These changes did not disable persistence checks.

See `evidence/test-output.txt` for the final raw result and `evidence/verification.json` for source hashes. Browser and clean-copy evidence are recorded separately.

Publication verification on October 14, 2026: [GitHub Actions run 38594994932](https://github.com/Amyvdev1/webhook-trust-lab/actions/runs/38594994932) passed all four jobs (Windows/Linux, Python 3.11/3.14) against implementation commit `835400b`. Each job ran the test suite and deterministic demo. This hosted result supplements, rather than replaces, the original local record.

This is a new implementation. The prior supplied draft's reported ten passing tests are not used as evidence for this version. No live vendor API, external side effect, distributed deployment, throughput/load test, or power-loss test was performed.
