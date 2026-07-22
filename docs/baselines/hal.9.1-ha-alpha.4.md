# hal.9.1-ha-alpha.4 baseline

## Scope

- Three persistent deferred transcript slots, each bounded to 240 characters.
- Five-minute to 24-hour expiration and strict refusal when all slots are full.
- FIFO dispatch by timestamped message ID even after a lower slot is reused.
- Immediate delivery when the recipient is already home consumes no slot.
- Delivery claim before audio and uncertain `review` quarantine after HA restart
  or a six-minute stuck claim.
- Explicit retry/discard only; no automatic replay from `review`.
- One-slot alpha migration preserves valid pending data and never extends an
  already expired legacy message.
- Transactional two-package provisioner with validation, rollback and no
  default restart.

## Source validation

- Family-message static safety contract: passed.
- Negative fixtures for fourth slot, restart reset, 255-character transcript,
  premature quarantine, missing review, external notification, templated action,
  legacy script ownership and default HA restart: passed.
- Seven state-model tests cover capacity/FIFO, immediate delivery, expiry,
  restart quarantine, stale claims, low-slot reuse and transcript bounds.
- Isolated Home Assistant `2026.7.2` configuration check with both real packages:
  passed; temporary files removed.
- Runtime test is non-audio and refuses occupied or uncertain slots.

## Source evidence

- Base Muse package SHA-256:
  `c91a475d04f878e684882d94e0d4628361e95528bde351359f301533940d86ad`.
- Family-message package SHA-256:
  `c081c2c30a0a5cd63f97ab367c5bae010e1da50da2734b6378b12755ba2fb3fa`.
- Isolated HA fixture SHA-256:
  `4eb855d8a2bc0ac4753209c447cb912acccb483619dc6334675765bf9e606712`.
- Transactional provisioner SHA-256:
  `1bb58f630178c3b66fd282339f93bc67daf783cd8c88f8ba28c344563ae4d0ba`.
- Safety checker SHA-256:
  `5eed9e5369a01bb5887138e4f680bb0107becbb3e28cb14bac7ea211d0d954d5`.
- Negative fixtures SHA-256:
  `456270b406db125952bb1de9af1a13245177219dfd480b5accb46fead7c8e4b8`.
- State-model SHA-256:
  `1619a7033bad160cb1a47f1d139662254bab80daf77b03c1a7b2cb38916708c1`.
- Runtime non-audio test SHA-256:
  `d49ee7ba8af4a4d2ccf8e65d2408ca6e0c44b56a6d905ea4483c8d5a08d94654`.

## Open gates

- Deploy and restart only after the uninterrupted firmware endurance run.
- Inspect and exercise any real legacy migration without exposing transcript
  contents in logs.
- Run the non-audio lifecycle test in the restarted production HA instance.
- Physically qualify three-slot fill/refusal, low-slot FIFO reuse, minimum
  expiry, restart quarantine and explicit retry/discard.
- Test distinct family person entities when more than one is available.
