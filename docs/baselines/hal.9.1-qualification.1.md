# Source baseline `hal.9.1-qualification.1`

## Scope

- Sixteen closed scenarios cover capacity, FIFO reuse, expiry, immediate
  delivery, restart persistence, quarantine, retry/discard and legacy migration.
- At least two recipients and three automatic deliveries are required.
- Exactly one immediate delivery, retry, discard and silent expiry are measured.
- Two uncertain deliveries enter review and automatic duplicates remain zero.
- Audible deliveries and carillons must match; all final slots are empty.
- Candidate OTA, two packages and provisioner hashes are bound.

## Validation

- Complete family-message fixture: passed.
- Candidate, runtime, final state, scenarios, metrics, consistency, boolean and
  time negative fixtures: rejected.
- No family transcript is present in the source or example record.

## Open gates

Run after endurance with consented test phrases and recipients. The example
remains failed until all physical audio and lifecycle observations complete.

## Source evidence

- Family-message evidence validator SHA-256:
  `6ee25c137ca4dc755b3d9e348c2c19a55b7a3d1a1fda61836641fa505b74f58d`.
- Positive and negative fixtures SHA-256:
  `69442e07a06f6bba95761cb405797b3db9eec6c688611c967daee22bd955702c`.
- Unqualified example record SHA-256:
  `8f6c478a7972fc545274a7fcdc903b13e4333c382e1ed288a4b5042d8c60e548`.
