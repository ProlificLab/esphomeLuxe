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
