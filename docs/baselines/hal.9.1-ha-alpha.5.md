# Home Assistant baseline `hal.9.1-ha-alpha.5`

## Scope

- Explicit two-to-four Muse temporary groups, still behind the existing
  default-off manual audio opt-in.
- Five-to-240-minute lifetime with a restorable Home Assistant timer.
- Persistent coordinator, member list, lifecycle state and transition claim.
- Per-player volume capture and restoration after Music Assistant confirms
  group membership.
- Queue transfer blocked during active, transitioning or review group states.
- Normal close and timer expiry share one deterministic unjoin path.
- Interrupted join/close, missing timer and stale transition quarantine to
  `review` without automatic restart cleanup.
- Human-confirmed recovery validates every persisted Muse and clears state only
  after all unjoin actions succeed.
- Transactional package publication, HA validation, rollback and no default
  restart.

## Source validation

- Music Assistant static safety contract: passed.
- Negative fixtures for default-on, eight players, day-long lifetime, broad
  player prefix, missing confirmation, unavailable player, ignored join timeout,
  expiry race, wrong timer event, presence automation, external notification,
  extra unjoin and default restart: passed.
- Five lifecycle model tests cover nominal grouping and relative volumes,
  invalid requests, join crash, partial close, watchdog quarantine, restored
  timer and explicit recovery.
- Isolated Home Assistant `2026.7.2` configuration check: passed with no disabled
  automation or error output.
- Shell syntax and Python bytecode compilation: passed.

## Source evidence

- Music Assistant package SHA-256:
  `bb4f97f651faf020accf3742dbabefb6a8573f03449afc0f51026be73c6710db`.
- Isolated HA fixture SHA-256:
  `4eb855d8a2bc0ac4753209c447cb912acccb483619dc6334675765bf9e606712`.
- Transactional provisioner SHA-256:
  `3f6cdc26cc75706461a3b8d343f88babeafe07d53007f5ce85c569cf34c8a0b7`.
- Safety checker SHA-256:
  `4a4a4a5bc2c567f3726e9d489fa214576c2ed7c603126cb36af5d59f42b6e083`.
- Negative fixtures SHA-256:
  `5f5dc8296b4e40f90e6c19eb47690fdbeddf0a88b5f60d8c4b2b0ec01868cfc7`.
- Lifecycle model SHA-256:
  `8c96ee641779f74ea3eb7e27bd792c371704feb390e99996666361cb65f6b707`.
- Production runtime test SHA-256:
  `982996ff9b62a8a46a41e196ae7d7aa346f7c91a16ec14403201e8e1c4e91a73`.

## Open gates

- Deploy and restart only after the uninterrupted firmware endurance run.
- Run the default-off production lifecycle guard before enabling any action.
- Add a second physical Muse and qualify music, radio and podcast transfers in
  both directions with elapsed position and playback state evidence.
- Qualify relative volumes, manual close, expiry close and HA restart with an
  active restored timer.
- Inject join and unjoin failures, prove `review`, and perform explicit recovery.
- Keep automatic presence following absent until the household defines and
  consents to an unambiguous room-presence policy.
