# Distribution baseline `hal.10-alpha.14`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `family_message_delivery` evidence as a hash-bound path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute queue package, base package and provisioner hashes from source.
- Enforce lifecycle, audio consistency, at-most-once and empty final state.

## Validation

- Standalone family-message evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound family-message records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not physical delivery evidence. Stable remains
blocked until the exact candidate passes the consented end-to-end protocol.

## Source evidence

- Qualification checker SHA-256:
  `1973ae2c8b292842717c297ad9fb3e8ee07eafcb589473c65116c391675d1d65`.
- Qualification fixtures SHA-256:
  `439e6e9ca040c6b05cb687e5aa74e6245f0298e40ae0ac06003bc8d67e354bef`.
- Qualification template SHA-256:
  `df68b7f6a72d827aa381a98af553a687b14b52973db2ecdeacd883ef5aaf8324`.
