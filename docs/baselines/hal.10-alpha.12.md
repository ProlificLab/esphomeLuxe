# Distribution baseline `hal.10-alpha.12`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `acoustic_guardian_physical` evidence as a hash-bound path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute package, preparer and policy-template hashes from source.
- Enforce consent, fixed classes, quality/resource bounds and safe rollback.

## Validation

- Standalone acoustic evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound acoustic records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not consent or physical evidence. Stable remains
blocked until the exact private candidate completes the observation protocol.

## Source evidence

- Qualification checker SHA-256:
  `738bbeacd010f86c875b0c84d2b502fe9fc2c690c28055debb7b4806c307e6f2`.
- Qualification fixtures SHA-256:
  `203b4f6db7711c4a2c055de431bf275aece32bd9a7638ccf7bf6ede96bd9827d`.
- Qualification template SHA-256:
  `c6d2daefd3bfe3e5ae455440a391b60a419017d6fdf115ad380237c30985483b`.
