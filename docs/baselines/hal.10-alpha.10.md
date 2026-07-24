# Distribution baseline `hal.10-alpha.10`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require `emergency_offline` and `offline_rescue_physical` to reference the
  exact same hash-bound record.
- Bind the record to candidate version and OTA SHA-256.
- Recompute rescue-package and read-only FAT-component hashes from source.
- Validate card immutability, all clips, fifteen scenarios and exact cycles.

## Validation

- Standalone rescue evidence positive and negative fixtures: passed.
- Positive stable qualification includes one shared bound record.
- Tampered, unbound and split-gate rescue records: rejected.
- Existing beta, modes, controls, LED, timer and endurance bindings remain.

## Open gates

The source and example are not physical evidence. Stable remains blocked until
the exact candidate and reviewed card pass the physical protocol.

## Source evidence

- Qualification checker SHA-256:
  `3c1115e423518aa30f58f0b57f8106374b1f962387596838434f2bed6f09f04d`.
- Qualification fixtures SHA-256:
  `82b5b4d0e1e5b626186d45eee699690f0217d718f3dafad478f7e130d0f3a683`.
- Qualification template SHA-256:
  `55752e2853ee460e308c8240867fdf0a7ae2ad78fe0f52e7c10a38c741bf66e3`.
