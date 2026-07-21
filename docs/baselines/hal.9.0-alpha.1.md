# Canary baseline `hal.9.0-alpha.1`

## Build

- ESPHome: `2025.10.5`, pinned Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,866,304` bytes, 91.8% of the OTA partition
- Application flash: `1,865,898` bytes, 91.8%
- RAM: `39,676` bytes, 12.1%
- MD5: `a069bf39adfd3e634f79828121528992`
- SHA-256: `a812919eb07b16ddc1cc5da7551d187f56c25b208f403b6436f831a620d5c4b9`

The image remains below the 93% roadmap target. The Okay Nabu calibration
configuration validates separately and is not part of the production image or
manifest.

## Implemented foundation

- Deterministic center-button single, double, long and triple gestures.
- Visible privacy mode with microphone mute, persisted switch state and reboot
  restoration.
- Bounded continuous conversation with explicit switch and five-minute timeout.
- Assist timer count, name and remaining-time telemetry, LED progress and a
  local completion sound.
- Home Assistant package for queued/urgent Piper announcements, day/night
  volume policy, whole-home targeting and privacy scripts.
- Safe package publication and one-time package-loader activation scripts.

The installed HA package SHA-256 is
`4cc45b01cd02ee3a779fc1472ffc8f8973a142277039cce8c8f60f8ff6e7e530`.

## Canary validation

- OTA deployment to `10.10.40.100`: passed on 2026-07-21.
- Reported version: `2025.3.1-hal.9.0-alpha.1`.
- Privacy on/off and continuous-conversation on/off transitions: passed.
- Privacy reboot persistence: passed in 16.78 seconds; cleanup returned to
  `waiting` and `healthy`.
- HA configuration check and package restart: passed on Core `2026.7.2`.
- Real queued Piper announcement after an HA restart: passed; HA recovered in
  8.18 seconds, playback began at 20.07 seconds and returned idle at 23.73
  seconds.
- Temporary startup test automation was removed and HA was restarted after a
  successful configuration check.

## Required before promotion

- Physically qualify all four center-button gestures and their debounce timing.
- Create, update, cancel and finish multiple named timers through Assist,
  including an HA reconnection during an active timer.
- Verify day/night, urgent interruption, chime, queue saturation and multiple
  speaker targets with real audio.
- Complete the existing 100-cycle TTS, 24-hour idle, power, Wi-Fi, jack and
  Hal/Nabu acoustic gates inherited from `hal.8`.

`hal.6` remains the published rollback image; the production update manifest is
unchanged.
