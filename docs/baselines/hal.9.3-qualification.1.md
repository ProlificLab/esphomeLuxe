# Source baseline `hal.9.3-qualification.1`

## Scope

- Fifteen closed scenarios cover both directions, audible voices, direction
  swap, visible listening, five exit paths, restoration and context isolation.
- At least five physical phrases per direction and a 15-second maximum latency
  are required.
- Five context resets and zero triggered Home Assistant actions are mandatory.
- Granite digest, two fixed pipelines, local-only mode and disabled tools are
  exact runtime requirements.
- Candidate version, OTA and all three interpreter source hashes are bound.

## Validation

- Complete interpreter fixture: passed.
- Candidate, runtime, scenario, metric, boolean and time negative fixtures:
  rejected.
- No bilingual acoustic behavior is claimed by this source baseline.

## Open gates

Run after endurance with consented French and English phrases on the canary.
The example remains failed until every physical observation is complete.

## Source evidence

- Interpreter evidence validator SHA-256:
  `e1bf12dbd3571b70276322b347303c57147f237c88625e382cb578711f38a380`.
- Positive and negative fixtures SHA-256:
  `3f002a454272f0597d5deeb76683f64db1ee9b6535c466c23707a356944fb8b2`.
- Unqualified example record SHA-256:
  `a4f21c7792beffd929a4d22995c63aada05d384d75d5e26f4591d3188f952b8f`.
