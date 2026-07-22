# Distribution baseline `hal.10-alpha.23`

## Scope

- Replace free-form evidence for seven core beta gates with one closed record.
- Bind candidate device, source commit, version and exact OTA SHA-256.
- Require ten firmware, Wi-Fi and HA recovery cycles, privacy reboot, one exact
  canary OTA, 100 audible TTS cycles and a retained verified `hal.6` artifact.
- Bind all seven raw logs by SHA-256 and require one identical record reference.

## Safety contract

- Wi-Fi and HA recovery remain strictly below 10 seconds; full reboot remains
  strictly below 20 seconds.
- Every series completes its exact count with zero manual intervention and ends
  `waiting`, `healthy`, with no voice error.
- TTS requires all 100 clips requested, completed and heard with zero failures,
  ring-buffer resets or voice errors.
- Rollback identity includes a lowercase SHA-256 and the immutable `hal.6` MD5,
  non-zero size, verified status and offline retention.
- Missing, tampered, unbound, split or escaping evidence is rejected.

## Validation

- Eight focused evidence tests cover identity, schema, time, strict boundaries,
  counts, cleanup, TTS, rollback and raw-log tampering.
- Forty-seven qualification tests cover positive beta/stable records and all
  existing plus core-canary negative paths.
- Physical execution remains closed until the active 24-hour endurance passes.

## Source evidence

- Core evidence checker SHA-256:
  `c2caca8d2b1ac0c235615c771937c5fddb83ce22a1903a8f517dd269734d005c`.
- Core evidence fixtures SHA-256:
  `98e67bede919f095e8bf254c99f8ab14695d1ca9ea95af711337d66c646ffdae`.
- Qualification checker SHA-256:
  `6689e72eac4094363a8d0fe1138d36de65d101afa0d4d729681d0f6f486f4146`.
- Qualification fixtures SHA-256:
  `dfe8c3953e32e2601936780269ce6150c148e1cecd732f1438f3298ebea23e56`.
- Core record template SHA-256:
  `f89e9757e6c500bc21af32f4bb35676afd97546903c6a78aa5fc0d3e140a5de9`.
- Qualification template SHA-256:
  `92ef3c6f06cb5c60d1ae336d64115da0dd4e2606c39574848eaa723482f84e7b`.
- Operator guide SHA-256:
  `b151f3baf1fb8ca02b61c7106c4c5040c10babd76e3bb1051b5b09e9559c2291`.
