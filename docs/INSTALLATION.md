# Installation

## Requirements

- Muse Luxe, data-capable USB cable and an 8 GB or larger recovery drive.
- Home Assistant with ESPHome, Wyoming/Piper and package loading enabled.
- Private `secrets.yaml` created from `secrets.example.yaml`.
- A retained copy of the `hal.6` recovery images and checksums.

## Canary workflow

1. Flash the upstream/recovery factory image over USB if the device is not
   reachable.
2. Provision Wi-Fi through Improv Serial; do not embed household credentials in
   Git.
3. Compile with the pinned command in `README.md`.
4. Upload only to one canary with ESPHome OTA.
5. Run configuration, size, reboot, timeout, privacy and TTS tests.
6. Publish HA packages with `publish_ha_file.sh`, run `ha core check`, then
   restart HA.
7. Keep every opt-in alert disabled until its synthetic and physical tests pass.

Never point the production update entity at an alpha manifest.

## Music Assistant

Use the stable Home Assistant app, not beta or nightly. After completing its
local account setup, confirm only the Supervisor-discovered Home Assistant
integration flow with `scripts/confirm_music_assistant_integration.py`. The
script refuses manual and OAuth flows so no HA password or long-lived token is
stored in the repository.

Add only explicitly selected Home Assistant players to the Music Assistant
player provider. For the current canary, the allowlist contains only
`media_player.raspiaudio_muse_luxe`. Publish
`home-assistant/packages/muse_music_assistant.yaml`, validate the HA
configuration, and restart HA before running the end-to-end test described in
`docs/MUSIC_ASSISTANT.md`.
