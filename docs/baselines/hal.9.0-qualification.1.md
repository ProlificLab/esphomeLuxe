# Source baseline `hal.9.0-qualification.1`

## Scope

- Exact project-version binding is mandatory; there is no default candidate.
- Existing evidence is refused before connecting to the canary.
- Privacy, continuous conversation, active timers and voice health are checked
  before the first state change.
- Four transitions are recorded in a closed order with timezone-aware times.
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
  `557ba6ac3437d1af6a793638acc96eac8f8084abadddb28b322d89ba27293830`.
- Evidence validator SHA-256:
  `67290ddbfd30589373a839f3e79f7e0774b69e1db634203dd9a64a0f8b7d123b`.
- Evidence fixtures SHA-256:
  `1e151c164a4bdbdab502d3aff736c5809273a75a6d9b676922419a11eba11976`.
- Source contract SHA-256:
  `2e59309a160d36c5471e3d0c43a82966d920463f38a344eac0346a3a30bb9418`.
- Negative source fixtures SHA-256:
  `e7085a958293e34a1bd7e036baf5a40c88dc5b2f1310c1eaf6041f73b426caa9`.
