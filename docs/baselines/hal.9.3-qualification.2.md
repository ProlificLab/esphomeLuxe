# Source baseline `hal.9.3-qualification.2`

## Scope

- Thirteen closed scenarios cover consent, audio probe, candidate validation,
  MQTT, cooldown, advisory-only behavior, retention, restart and rollback.
- All four fixed classes require at least two observed hours and one event.
- False positives are quantified and limited to one per observed hour.
- RMS is coherent and event CPU may rise by at most 30 percentage points.
- Transcription, restart opt-in and physical actions remain disabled.
- Candidate OTA and three repository sources are bound; only the private
  candidate hash is retained.

## Validation

- Complete acoustic-guardian fixture: passed.
- Candidate, consent, runtime, scenario, metric, bounds, boolean and time
  negative fixtures: rejected.
- No camera audio has been enabled by this source baseline.

## Open gates

Run after endurance and explicit household consent. The example remains failed
until the Chuwi and physical camera complete the full observation period.

## Source evidence

- Acoustic evidence validator SHA-256:
  `8b79f91faebda39f8d030dac9b7b7adf4caf28a1cfaf9d93f2baf866d13f8723`.
- Positive and negative fixtures SHA-256:
  `06a387eea7d48d2b7aa5d92b5150f1a9296a44c70ed37c1a04bea4e99e3a4ae0`.
- Unqualified example record SHA-256:
  `79dad24f4609d411365d829589e304805f77d1484d9b584a270f262b984fdd17`.
