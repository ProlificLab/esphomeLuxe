# Canary baseline `hal.7-alpha.3`

## Build

- ESPHome: `2025.10.5`, Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,847,984` bytes, 90.9% of the OTA partition
- Application flash: `1,847,586` bytes, 90.9%
- RAM: `39,068` bytes, 11.9%
- MD5: `122274127ecfcee5cdcf2e888acadd79`
- SHA-256: `187e4ccb1baf4c8dd69976dfe3e7a39cb098107e904c0b8069b1692a01a223f7`

The primary image now embeds only Okay Hal. Removing the unused Okay Nabu
model saved about 81 KiB and moved the firmware below the 93% roadmap target.

## Architecture

The configuration is split into `hardware`, `audio`, `voice`, `ui`,
`recovery`, `diagnostics` and `updates` packages. A clean build after the split
used 12 fewer application bytes than the equivalent monolithic build.

The final SPIFFS partition keeps the same offset and size; only its incorrect
`littlefs` label was corrected, removing the partition-table warning.

## Canary validation

- OTA to `10.10.40.100`: passed on 2026-07-21.
- Reported version: `2025.3.1-hal.7-alpha.3`.
- Post-boot state: `healthy` and `waiting`.
- Initial heap free: about 192 KiB; PSRAM free: about 4.17 MiB.
- Voice errors and timeouts after boot: zero.
- Software reboot recovery: passed in 17.04 seconds.
- Local startup sound: passed during boot.
- Ten Home Assistant Core restarts: passed. The final automated series of eight
  recovered from `offline` in 8.07-8.76 seconds (8.34 seconds average) and
  advanced the reconnect counter once per cycle.
- Twenty-five network announcement cycles: passed. The final measured series
  averaged 3.75 seconds, lost only 2,188 heap bytes and gained 268 PSRAM bytes
  after a fresh post-test diagnostic sample.

A direct media URL hosted on the Mac was intentionally unreachable from the
IoT VLAN. The attempted playback was stopped through the encrypted API and the
device returned to `healthy`, `waiting` and media `idle` without an error. The
same WAV published by Home Assistant then completed normally, confirming the
intended inter-VLAN media path.

## Still required before promotion

- Ten physical power cycles.
- Ten Wi-Fi interruptions and recoveries.
- Seventy-five more announcement cycles plus actual generated TTS endurance.
- Wake-word, volume, mute, jack and forced-timeout tests.
- A separate Okay Nabu calibration image and measured comparison.

`hal.6` remains the published rollback image.
