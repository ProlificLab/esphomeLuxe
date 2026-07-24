# Source baseline `hal.9.0-qualification.1`

## Scope

- Exact project-version binding is mandatory; there is no default candidate.
- Existing evidence is refused before connecting to the canary.
- Privacy, continuous conversation, active timers and voice health are checked
  before the first state change.
- Four transitions are recorded in a closed order with timezone-aware times.
- Continuous listening is bound to the firmware's `busy` health state; the
  runtime, evidence validator and recovery package are checked together.
- Both ESPHome API switches, privacy restoration policy and continuous
  start/stop actions are part of the same source contract.
- Voice errors, timeouts and recoveries must remain unchanged.
- A `finally` path disables both modes and requires fresh switch publications
  before accepting `waiting/healthy` after a failure.
- Passing evidence records the observed cleanup time and is atomically
  published only after cleanup succeeds.
- Physical buttons, audio and LED observations remain an explicit manual gate.

## Source validation

- Evidence validator positive fixture: passed.
- Wrong version, missing/reordered case, wrong mode state, changed/malformed
  diagnostics, unsafe cleanup and non-monotonic time fixtures: rejected.
- Runtime source contract and cleanup/publication ordering: passed.
- Negative source fixtures for missing timer, cleanup, atomic-write and version
  guards: rejected.
- Python bytecode compilation: passed.

## Open gates

- Do not execute while the current `hal.9.0-alpha.2` endurance run is active.
- After the run, deploy the paired `hal.9.0-alpha.5` candidate to one canary.
- Run the transactional API test and independently observe every physical
  control and LED state listed in `docs/MODES.md`.
- This source baseline is not physical evidence and cannot pass a beta or stable
  qualification gate by itself.

## Source evidence

- Transactional runtime SHA-256:
  `e921ad3c36fb3304602612487743d5ec304e9c81dba613f29c71a512e9fa5f17`.
- Evidence validator SHA-256:
  `522dcce412ea32562a1c545436da214ca394640bbcb4221f65f28424f33df963`.
- Evidence fixtures SHA-256:
  `2ff899063c77220701314fa2eb6646bd82cc4fcba1f602126f7059e649bfad78`.
- Source contract SHA-256:
  `d2b69c84207d112a43c7333ee8d89aca4849ef4bce68b4bd91a31a540477288b`.
- Negative source fixtures SHA-256:
  `c5f23ca41d7a0648d916bb447e643f84d47cbf925aab0225da916029a6770e45`.
