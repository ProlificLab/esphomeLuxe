# hal.9.3-ha-alpha.3 baseline

## Acoustic guardian source scope

- Frigate's built-in CPU classifier is the sole local detection engine.
- Consent-bound candidate generator selects one existing go2rtc input and
  never modifies the active Frigate configuration in place.
- Closed labels: `fire_alarm`, `glass`, `crying` and `bark`.
- Per-label confidence threshold, RMS gate, event timeout and maximum one-day
  detection retention are enforced before a candidate can be generated.
- Automatic audio transcription is forced off.
- Home Assistant defaults to off, returns to off after restart, allowlists
  camera and label, waits ten seconds after arming, rate-limits announcements
  and records corroboration state.
- Critical actions remain unreachable; every result is advisory.

## Validation

- Static Home Assistant safety contract: passed.
- Positive candidate generation fixture: passed.
- Negative fixtures for missing consent, long retention, speech collection,
  direct camera connection, timezone-free approval, global audio, global
  transcription and siren action: passed.
- Live Chuwi inventory was read without changes: Frigate VM 110 has 6 vCPU,
  12 GiB RAM, eleven same-name go2rtc cameras and no active audio role.
- Current live retention is 14 days for detections and 30 days for alerts, so
  direct audio activation was correctly refused as unsafe.
- Frigate container exposes its official `--validate-config` path: verified.
- Live Frigate version: `0.17.2-3d4dd3a`.
- Synthetic candidate generation also passed inside VM 110 with mode `0600`;
  all temporary files were removed afterward.

## Source evidence

- Home Assistant package SHA-256:
  `3a34f34b33081c4db13545257e310ce8cc0e096ba947495fa7c7fecc4f421c4e`.
- Candidate preparer SHA-256:
  `efdf64439a7d1f90fd6230b636711f264293c37f24ac71909ceb8da23d162e76`.
- Safety checker SHA-256:
  `6ee6f1be0e6b8070635f713d28473e49c50417bc7fd71bd6ae52a1f4a74bc085`.
- Negative test SHA-256:
  `2b73e7a71c18aaeaf2434594666e12340b9a3b8b6898e5330a4931d398162dce`.
- Disabled policy example SHA-256:
  `e6e0901fa18df728b36c21305cffcba702aa312eaf6ef96e0b4cf49fa108b774`.

## Open gates

- Select a camera/room and record explicit household consent.
- Probe that exact go2rtc input for a real audio channel.
- Generate and validate a private candidate inside VM 110.
- Apply only in a maintenance window after backup, then measure CPU, RMS,
  false positives, MQTT lifecycle and one-day deletion physically.
- Keep all real camera audio disabled until those gates are reviewed.
