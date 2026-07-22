# Source baseline `hal.9.0-qualification.4`

## Scope

- Twelve closed scenarios cover concurrency, pause/resume, duration change,
  cancellation, queue ordering, HA loss, reconnect and urgent interruption.
- Exact metrics require two distinct names, all four checkpoints once in day
  and night, zero replay and one local completion sound during HA loss.
- Observer and recent timezone-aware observation time are mandatory.
- Candidate version, OTA SHA-256 and both HA package SHA-256 values are exact.

## Validation

- Complete physical timer fixture: passed.
- Candidate binding, scenario set/result/evidence, metrics, names and
  observation-time negative fixtures: rejected.
- No physical timer behavior is claimed by this source baseline.

## Open gates

Run only after endurance and paired firmware/HA deployment. Every example
result and metric remains unqualified until observed on the canary.

## Source evidence

- Timer evidence validator SHA-256:
  `23e66a14aa0584a74e1aaeff175908fcf9e8af1d65b71b7f9367b95c9b6131bd`.
- Positive and negative fixtures SHA-256:
  `b605f360ee3b5197c73963472b6c95fe3f8a759c43973ab4d661a793350cebfa`.
- Unqualified example record SHA-256:
  `8591529459cc52598fec8ce7f9010509ebdc980b806f8acd7e4cee7c948c36fe`.
