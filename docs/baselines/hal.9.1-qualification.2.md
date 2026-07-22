# Qualification baseline `hal.9.1-qualification.2`

## Scope

- Bind physical intercom evidence to the candidate and all source contracts.
- Close 31 scenarios across two fixed players and two trusted button devices.
- Require 20 calls per direction, bilateral relays and all terminal paths.
- Recompute recognition rate and audible/carillon/LED count consistency.
- Require bounded latency, zero ghost/raw/transcript/external state and cleanup.

## Validation

- Complete positive evidence fixture: passed.
- Candidate hashes, players/devices, runtime, scenarios, metrics, final state and
  observation-time negative fixtures: rejected.
- Qualification checker accepts only hash-bound evidence for the stable gate.
- Tampered and unbound intercom records: rejected.

## Open gates

The failed example and source tests are not physical evidence. Run the protocol
only with the second satellite and after the active endurance window.

## Source evidence

- Evidence validator SHA-256:
  `fd47092510403f54f8b603a331b68e34513f20a03983034a528df00d6fda8832`.
- Evidence fixtures SHA-256:
  `1978126620418cd939e0d306827f71bd40f429245afc4dabf3196d4a7ed170b9`.
- Unqualified example SHA-256:
  `807b5d2b1f9fc6376409df7869fb5294752c5db169d0269d8d730377db69634c`.
