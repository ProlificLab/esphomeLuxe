# Source baseline `hal.9.2-qualification.4`

## Scope

- Alerts accept only fresh person events from two closed cameras.
- A persistent seven-ID FIFO replaces last-event-only deduplication.
- Confidence, global cooldown, night mode, opt-in, ID and event-age bounds are
  mandatory before claiming an event.
- Twenty-seven scenarios cover all edges, restart persistence and audible
  delivery parity.
- Candidate, OTA, packages and four policy/test hashes are exact.

## Validation

- Static source contract and eight unsafe mutations: passed and rejected.
- Six state-model tests cover FIFO, cross-camera cooldown, stale/future input,
  privacy filters and non-mutating rejection.
- Complete video-alert evidence fixture: passed.
- Candidate binding, runtime, scenarios, metrics, booleans, final state and time
  negative fixtures: rejected.
- No physical MQTT or audible behavior is claimed by this source baseline.

## Open gates

Run synthetic MQTT injections only after endurance, with no images or identity
data. The example remains failed until all audible observations are complete.

## Source evidence

- Video-alert safety checker SHA-256:
  `eff807da1f8f0ce7666a83f1f75ffd6635fbe9ab4fc5325064b43f84d0b8385c`.
- Safety negative fixtures SHA-256:
  `3c8e589c157efcd897364991b1ebc2da820fc8ca343e078b4ea77484b427de4c`.
- State model tests SHA-256:
  `2d7895d15e1e8b9de9a96f17207c46d78545f4e4feaa9735c316ddffb5735457`.
- Video-alert evidence validator SHA-256:
  `61ef6f9430a18c6c2fe5786fc05d300d1c323d1e9b2d1a06b4410fffca8a3d74`.
- Evidence positive and negative fixtures SHA-256:
  `ae3ef4256235ffdd6e4ff32445af0fcd54fe9acc01c3c56565cf2378aeb6555a`.
- Unqualified example record SHA-256:
  `7034ef31a0d36dfb859851af090f7c80a6d2461e96ec3c48cc9a947dea7e111a`.
