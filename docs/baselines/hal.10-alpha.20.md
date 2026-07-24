# Distribution baseline `hal.10-alpha.20`

## Scope

- Make `music_transfer_two_satellite` a hash-bound stable evidence gate.
- Bind candidate, package, checker, model, live HA test and provisioner.
- Reject tampered, unbound, stale, incomplete or cosmetically passing evidence.

## Validation

- Forty-three qualification tests: passed.
- Tampered and unbound music-transfer records: rejected.
- Stable remains blocked until the exact physical record passes.

## Source evidence

- Qualification checker SHA-256: `815e05899eec43df204c89adf7fb84bd265eb7ecb41ae71ca85e76ef6c3ecc2c`.
- Qualification fixtures SHA-256: `a04dc65cd2456faed74a74d1962331261a9db93592b4eb9df5f66fb2a2a7d235`.
- Qualification template SHA-256: `150a890b9f576db0a36ffdf6843d290623c7d0c3376a4a009a6bae4392b45870`.
