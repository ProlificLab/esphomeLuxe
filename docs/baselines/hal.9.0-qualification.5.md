# Source baseline `hal.9.0-qualification.5`

## Scope

- Fifteen closed scenarios cover every gesture, all fixed clips, card insertion,
  diagnostics, HA loss/reconnect, reboot, privacy and return to waiting.
- The six allowlisted clips must each be heard at least once.
- Exactly one HA disconnect/reconnect cycle and one rescue-mode reboot are
  recorded, with zero unexpected media errors.
- Card label, file set and identical before/after manifest hashes are required.
- Candidate version, OTA, package and read-only component hashes are exact.

## Validation

- Complete offline-rescue fixture: passed.
- Candidate binding, card identity/content/hash, scenario, metrics and time
  negative fixtures: rejected.
- No microSD or physical behavior is claimed by this source baseline.

## Open gates

Run only after endurance with a family-reviewed rescue card. The example stays
failed until all observations have been performed on the canary.

## Source evidence

- Offline-rescue evidence validator SHA-256:
  `12599547eb7b8675cc752f9ec7c21ac8054d0eb3cd0272d8feaaf6137a191f6c`.
- Positive and negative fixtures SHA-256:
  `ca17913fe4d8db741bd791aa560b739577f38e88edc2bae632ae7e65e2436a48`.
- Unqualified example record SHA-256:
  `b5f8e955066c976a8d15de193529f16d29b1072de0f17d81384cf940b18dcd52`.
