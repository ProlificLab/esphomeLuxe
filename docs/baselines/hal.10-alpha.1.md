# Distribution baseline `hal.10-alpha.1`

## Implemented

- Channel-aware `development`, `beta` and `stable` manifest generation.
- Automatic CI output remains `development` only.
- Beta requires `ALLOW_BETA=1`, a non-alpha version and a non-empty, recognized
  qualification record.
- Stable requires `ALLOW_STABLE=1`, a qualification record and a version with
  no `alpha`, `beta` or `rc` marker.
- Production `manifest_update.json` is CI-locked to the archived `hal.6` MD5,
  version and private OTA path.
- Release verifier checks schema, channel, versioned filename and artifact MD5.
- Build metadata records version, channel, size, hashes, pinned ESPHome image
  and ESP-IDF version.
- CI uploads release directories recursively.
- GitHub checkout and artifact actions are pinned to `v7.0.1` commit SHAs for
  the current Node 24 runner contract.
- Installation, recovery/diagnosis, privacy and release-channel guides added.
- Structured crash, audio, wake-word and hardware issue forms added.

## Validation

- Development package: `2025.3.1-hal.9.0-alpha.1`, verified successfully.
- OTA MD5: `a069bf39adfd3e634f79828121528992`.
- OTA SHA-256:
  `a812919eb07b16ddc1cc5da7551d187f56c25b208f403b6436f831a620d5c4b9`.
- Beta packaging without authorization: rejected.
- Stable packaging of the alpha even with authorization: rejected.
- Production manifest guard: passed and remains `hal.6`.
- Shell syntax, ShellCheck, Python compilation and whitespace checks: passed.

## Open gates

- Do not create a stable channel until all inherited 100-cycle TTS, 24-hour
  idle, physical button/jack, Wi-Fi/power and acoustic calibration gates pass.
- Add an automated changelog and dependency-diff report between promoted tags.
- Perform the installation and rollback guides end-to-end with a second person
  who has no repository context.
- Submit generic, hardware-independent fixes upstream only after canary/beta
  evidence and removal of private infrastructure assumptions.
