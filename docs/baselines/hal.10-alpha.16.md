# Distribution baseline `hal.10-alpha.16`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `house_intelligence_freshness` evidence as a hash-bound path.
- Bind the record to candidate version, OTA and exact narrator package.
- Bind OPNsense controller/ACL and Proxmox/Frigate read-only policy sources.
- Reject stale, incomplete, writable or externally delivered evidence.

## Validation

- Standalone house-intelligence evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound house-intelligence records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not physical telemetry evidence. Stable remains
blocked until the exact candidate passes the maintenance-window protocol.

## Source evidence

- Qualification checker SHA-256:
  `ad4d51ce82fe79b25d2bb4a1befc8d4cbcaa695146d371a2a55339014f1d737c`.
- Qualification fixtures SHA-256:
  `266b28ff49130285cd00565f50c022dcd3ba1380fdcc47b1ba871bb48d5b4cae`.
- Qualification template SHA-256:
  `5f29fa2e41ddb033b7a38d6c9fdc5970973799ac6de87999fec69140fed2347f`.
