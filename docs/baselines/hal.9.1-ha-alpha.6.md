# Source baseline `hal.9.1-ha-alpha.6`

## Scope

- Reject unknown and unavailable players before any intercom state mutation.
- Emit call, acceptance and relay carillons before claiming their active state.
- Bind accept, decline, hang-up and every queued relay to the exact session ID.
- Permit both call directions only through explicit fixed room names.
- Route single/double central-button gestures through two trusted device names.
- Keep transcripts transient, bounded to 240 characters and free of raw audio.

## Validation

- Static safety contract and twelve unsafe source mutations: passed and rejected.
- Seven state-model tests cover both directions, unavailable players, stale
  queued relays, session controls, trusted buttons, timeouts and transcripts.
- Main ESPHome configuration with the shared gesture publisher: passed.
- Offline rescue still binds quadruple-click to its local toggle and event.
- Main OTA remains below the achieved target: 1,888,912 bytes (92.9%).
- Home Assistant package and French sentence YAML parsing: passed.
- No firmware deployment, Home Assistant restart or physical call is claimed.

## Open gates

Deploy the reviewed cuisine identity only after firmware endurance. The exact
candidate still needs the complete two-satellite protocol and transcript audit.

## Source evidence

- Common announcement package SHA-256:
  `78bc0c18d0e7638d8f6365375f1a84a01b4bb0bd1640ecb89b6d9d0dad1a5bc1`.
- Intercom package SHA-256:
  `74d561a95b92ddbe86e1f3d7764e73e9291514207df9c64d243e0a40082331bd`.
- French sentences SHA-256:
  `5343178db9e91e3f5c0cc755263df6ccb8b526995e6d51a6b0c1e95ed437f13e`.
- Firmware UI SHA-256:
  `b1589863d05bfa09ce7f967c22b76e3b228ca006f73ef7956b02db0163283897`.
- Firmware recovery SHA-256:
  `184387416c033accd9174ec60d0ca151b28adce62cff87540f580581834cc422`.
- Safety checker SHA-256:
  `f977fcbb290fc9ee9a1e4eef594a31ecf4eac6600387adcce01b2562289bf5a6`.
- Safety negative fixtures SHA-256:
  `698579ad00b20aedfb0a1cffbbce5f742d748f043be3e5d405a968d9a7342ac3`.
- State model SHA-256:
  `82e8bc46b75fa0d9dcd0dee4d6b5ef2e7bf2c085788e41dcc895f1440837603f`.
- HA lifecycle test SHA-256:
  `13f84e9c28e90c02f153c61e7ac8f30811949883c56eeed1a22bfe7dd03e2681`.
- Offline-rescue safety checker SHA-256:
  `ebe260234c51c681d4cec7e9d97074f76b8c2345e89403aa41308ae4b502e2aa`.
- Offline-rescue negative fixtures SHA-256:
  `0005fe71ad97d589b279316587b35fbebc6abef8a7f303bde36950a2dfdee540`.
