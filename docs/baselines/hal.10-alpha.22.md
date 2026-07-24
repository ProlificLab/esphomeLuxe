# hal.10-alpha.22 baseline

## Scope

- Separate private canary publication from physical OTA installation.
- Upload the exact reviewed artifact through the pinned ESPHome `espota2` code.
- Require explicit confirmations and encrypted post-boot health checks.
- Keep `hal.6` rollback exact, manual and independent from canary failure logic.

## Safety contract

- Canary install repeats clean-tree, 24-hour, version, SHA-256, MD5 and URL gates.
- The OTA password is read from a read-only secrets mount and never printed.
- A successful upload is not success until exact version, `waiting`, `healthy`
  and an empty voice error are observed through the encrypted API.
- Rollback requires a retained private artifact matching both an explicit
  SHA-256 and the immutable `hal.6` manifest MD5.
- No script automatically rolls back or writes the production root manifest.

## Verification

- Four offline install/rollback safety tests cover healthy boot, wrong version,
  degraded/error states, digest drift, manifest drift, operation ordering and
  separation of rollback.
- Shell syntax and Python bytecode checks run alongside the complete firmware CI.
- Physical installation remains locked until the active 24-hour endurance
  summary has passed review.
