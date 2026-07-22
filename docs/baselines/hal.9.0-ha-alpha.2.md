# hal.9.0-ha-alpha.2 baseline

## Scope

- Opt-in nearest-timer announcements at 300, 60, 30 and 10 seconds.
- Normal-tick guard rejects startup, reconnect, duration-jump and timer-switch
  replay rather than producing duplicate or stale speech.
- Existing day/night volume, bounded queue and volume restoration reused.
- Non-urgent announcements wait for music, voice start, listening, answering
  and continuous conversation; urgent interruption remains explicit.
- Native ESPHome multi-timer telemetry, LED countdown and local completion
  sound remain unchanged, preserving the 92.9% firmware image.
- Transactional two-package provisioner validates and rolls back without a
  default Home Assistant restart.

## Source validation

- Timer-coach static safety contract: passed.
- Negative fixtures for default-on, extra checkpoint, reconnect replay, urgent
  priority, external notification, conversation bypass and default restart:
  passed.
- Five model tests cover exact checkpoint set, disabled/invalid state, reconnect
  and duration jumps, bounded tick jitter and audio/conversation contention.
- Isolated Home Assistant `2026.7.2` configuration check with both real
  packages: passed.
- Shell syntax and Python bytecode compilation: passed.

## Source evidence

- Base Muse package SHA-256:
  `17bc501bfe9c21637bed9829d016abf4fe665764ab2c3a8fc7634e2a1d2b4bdf`.
- Timer-coach package SHA-256:
  `3e66ff8faf849f7d80e0bf64e8b8188c6876b986bf557e66d2766793e463bde7`.
- Isolated HA fixture SHA-256:
  `4eb855d8a2bc0ac4753209c447cb912acccb483619dc6334675765bf9e606712`.
- Transactional provisioner SHA-256:
  `26ee379f616c15bfaf41d38457efb622c6dcc11e9b6dfc29cb59f099d441f36d`.
- Safety checker SHA-256:
  `4907b15572886d993e1c2f1e2d9449528b241a10c119ee3b9e2e747c1ce5b3cf`.
- Negative fixtures SHA-256:
  `f3115e21aec1a837beff0ba0da7b679ae0911ecf74ead7a8aa7a2afa8bbf8fee`.
- State-model SHA-256:
  `342d0376509d1c70fa98677433e10a97a30bb5c497fae89974cca64b0557c12c`.

## Open gates

- Deploy and restart only after the uninterrupted firmware endurance run.
- Keep checkpoint announcements off until physical timer tests begin.
- Qualify two named timers with pause, resume, duration update and cancellation.
- Verify day/night volume, queueing behind music and continuous conversation,
  urgent interruption and local completion through an HA disconnect/reconnect.
- Confirm no missed checkpoint is replayed after reconnect.
