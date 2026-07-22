# Source baseline `hal.9.0-ha-alpha.5`

## Scope

- Preserve the bounded 25-entry announcement queue and ten-minute normal wait.
- Let intercom callers require one exact session and status without changing
  normal announcement callers.
- Recheck those guards after the busy wait and immediately before Piper.
- Restore the previous volume when a post-chime intercom guard expires.

## Validation

- Static announcement safety contract: passed.
- Ten unsafe source mutations, including both queue guard bypasses: rejected.
- Home Assistant package YAML parsing: passed.
- No Home Assistant publication, restart or physical announcement is claimed.

## Open gates

The existing announcement qualification remains physical and hash-bound. A new
candidate must use the exact updated package and complete that protocol after
the active firmware endurance window.

## Source evidence

- Common announcement package SHA-256:
  `78bc0c18d0e7638d8f6365375f1a84a01b4bb0bd1640ecb89b6d9d0dad1a5bc1`.
- Safety checker SHA-256:
  `6becf13b49e07d68b66ea88c9942072743707129df50e5ef817dd0e4866e6b9c`.
- Safety negative fixtures SHA-256:
  `5a039ef702a70e6437ce077235492e2da2af1454c453324b5882b248657d451b`.
