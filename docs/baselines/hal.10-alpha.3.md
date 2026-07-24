# hal.10 alpha 3 baseline

## Scope

- Strict JSON qualification schema linked to channel, version, full source
  commit and exact production OTA SHA-256.
- Twelve mandatory beta gates and 24 mandatory stable gates, each with a true
  boolean and non-placeholder evidence.
- Reviewer, fresh timezone-aware review time, canary identity, compatibility
  matrix, feature scope and explicit open-gate list.
- Stable rejects every open gate and every alpha, beta or release-candidate
  version.
- Promotion rejects a dirty worktree or a target other than checked-out HEAD.
- Pinned clean ESPHome rebuild occurs before qualification verification.
- Beta/stable OTA paths include the exact version instead of overwriting a
  mutable `firmware.ota.bin`.
- Artifact, record, changelog, dependency diff, metadata and checksums publish
  before the activation manifest; nothing may publish after it.
- Build metadata now records the source commit.

## Validation

- Qualification checker: eight positive/negative unit cases passed.
- Release verifier: eight channel, path, hash and version cases passed.
- Promotion ordering checker and eight negative mutations passed.
- Existing development artifact retained SHA-256
  `999192bf42207945df7c2eea205de3772502d53ca1a0f0aa4372870a76e634d8`.
- Development manifest and source-commit build metadata verification passed.
- Full repository CI: required on the exact commit before merge; use the PR
  check as the authoritative result rather than copying a mutable status here.

## Open gates

- The current alpha firmware is intentionally ineligible for beta or stable.
- Complete the active 24-hour endurance campaign and every physical gate named
  in `docs/qualification-record.example.json`.
- Have a second person execute install, diagnosis and rollback using only the
  documentation.
- No beta/stable manifest has been published by this source-only change.
