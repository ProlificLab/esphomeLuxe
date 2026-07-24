# Source baseline `hal.9.1-ha-alpha.7`

## Scope

- Keep transfer and temporary grouping manual and disabled by default.
- Restrict both transfer endpoints and every group member to available Muse players.
- Preserve bounded groups, persisted claims, volume restoration and review recovery.

## Validation

- Safety contract and fourteen unsafe mutations: passed and rejected.
- Five lifecycle model tests: passed.
- Home Assistant package YAML parsing: passed.
- No publication, restart, transfer or physical grouping is claimed.

## Source evidence

- Package SHA-256: `bc47e7edf6981b08eba50e307d218120e98ed220ded01495892b0206ed58c981`.
- Safety checker SHA-256: `6630b10da2c07c588e31cc74931d1d2c26f334de131d9ec5ef6d39933c8ffb5d`.
- Negative fixtures SHA-256: `38629af0669fb56af13163928b617ea60d935b09f001cd01ce251620fdfbb6b8`.
- Lifecycle model SHA-256: `8c96ee641779f74ea3eb7e27bd792c371704feb390e99996666361cb65f6b707`.
