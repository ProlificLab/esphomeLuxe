# Distribution baseline `hal.10-alpha.28`

## Scope

- Separate the retired OTA upload credential from new API verification.
- Activate the complete new local set only after exact healthy boot.
- Retire the transition file with a resumable local state change.

## Safety contract

- Bundle, three-real-secret audit, endurance and exact artifact preflights run
  before a dedicated literal rotation confirmation.
- Upload receives only `transition-ota.yaml`; post-boot verification receives
  only the new `secrets.yaml`.
- Existing exact-install guards still require a clean worktree and pinned OTA.
- Active secrets are atomically replaced only after encrypted verification.
- Interrupted activation can resume; unrelated or partial active sets fail.
- Transition retirement follows durable active replacement and durable state.

## Validation

- Three offline tests cover replacement/retirement/resume, foreign and partial
  active-set refusal, and closed ordering through upload, verify and activation.
- Existing four exact-install and five bundle tests remain mandatory.
- No transition command is executed during the active endurance run.

## Source evidence

- Exact canary installer SHA-256:
  `51db47242f36011af80b61afdef76573fcbeb77707476205917a3e5f12e2e984`.
- Rotation orchestrator SHA-256:
  `a54910fad4dd2282a28b2a95a3c267382311b5f8b8084f61169f222c0dd6a988`.
- Resumable local activator SHA-256:
  `54616e2a1ecaed24c294f8e4df759d3f5a1f17a46821c3960b31ab054082c6fe`.
- Offline fixtures SHA-256:
  `455beec5885061bd94f3614cbc0fdb3e0779316c45ab64b2f87942859d4772a9`.
- Operator guide SHA-256:
  `65e5d2e6ac09919f47a2e353477f7db3183438b3c981af51794755c56e78f723`.
