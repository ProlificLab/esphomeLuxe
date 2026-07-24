# Distribution baseline `hal.10-alpha.18`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `camera_alerts_deduplicated` evidence as a hash-bound path.
- Bind the record to candidate version, OTA, packages, safety/model sources,
  MQTT provisioning and Frigate read-only policy.
- Require exact audible/accepted parity and persistent bounded deduplication.
- Reject stale, writable, identifying or externally delivered evidence.

## Validation

- Standalone video-alert evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound video-alert records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not physical alert evidence. Stable remains blocked
until the exact candidate passes the consented MQTT protocol.

## Source evidence

- Qualification checker SHA-256:
  `75fc4df2d6ea41c85f2d8b073f128f23070e90b1ee819046a3f60e24c2804547`.
- Qualification fixtures SHA-256:
  `22e61d9946faa897569c2c855629edfc70a7dfb13933fb9ec1bc50379ef9f715`.
- Qualification template SHA-256:
  `3a78573f04551a774b9a2aa6a4d3b85e280091281fc2d1251610f2dd3d5a8c71`.
