# Distribution baseline `hal.10-alpha.11`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `interpreter_bilingual` evidence as a hash-bound path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute package, configurator and local-sentence hashes from source.
- Enforce pinned local/tool-free runtime and physical bilingual measurements.

## Validation

- Standalone interpreter evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound interpreter records: rejected.
- Existing beta and all previously structured stable bindings remain active.

## Open gates

The source and example are not physical evidence. Stable remains blocked until
the exact candidate passes every bilingual observation.

## Source evidence

- Qualification checker SHA-256:
  `45ccbcbe9496a4bee0754c3543cbe5c35b4431420149dcc5442e830aedb4df51`.
- Qualification fixtures SHA-256:
  `6b89db7dac0c108644aaac946f40a0b814eb9e85c164d81f7f4cc2ada4095a7f`.
- Qualification template SHA-256:
  `96aaa768eabbf37a07c559c2d926f2c773511b26a20f660f57e20fa84a936b1b`.
