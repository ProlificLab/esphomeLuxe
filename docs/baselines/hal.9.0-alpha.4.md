# Source baseline `hal.9.0-alpha.4`

## Scope

This source candidate restores the roadmap flash target without removing voice,
music codecs, encrypted API/OTA, HTTP updates or offline rescue audio.

- Replace ESPHome's generic multi-platform `debug` component with a local ESP32
  component for heap, largest block, PSRAM, maximum loop time and reset reason.
- Compile the primary image at `ERROR`; runtime health, counters and recovery
  reasons remain exposed through Home Assistant entities.
- Provide a separate `WARN` USB diagnostic image with a distinct node/version
  and no HTTP updater.
- Remove only CPU-frequency telemetry because the firmware fixes it at 240 MHz.

## Build

- Pinned ESPHome: `2025.10.5`; ESP-IDF: `5.4.2`.
- Private local candidate OTA: `1,888,816` bytes, `92.9%`.
- RAM: `40,444` bytes, `12.3%`.
- Private local pinned-build SHA-256:
  `f3d3dad6258494dcc6286becb6c6a6f129789780b7a1dd69ee37f3da7cf7cb1b`.
- Clean CI run `29885309117` passed with non-production example secrets. Its
  synthetic OTA is `1,888,800` bytes with SHA-256
  `194ae4c5a75daaffcdddc2f5aa01778f336cf0232f2f98535f97b27df01e86fc`.
- The 16-byte difference is secret-fixture dependent. CI proves source and size
  gates; beta/stable qualification must bind a fresh private rebuild instead of
  the synthetic CI firmware.

## Gates

- Production and diagnostic configuration validation: prepared for CI.
- Source safety checker requires all dynamic diagnostics, production `ERROR`,
  diagnostic `WARN`, distinct identity and absence of HTTP self-update.
- The former 93% warning is now a blocking CI gate with exact-boundary tests.
- Physical diagnostic parity, rescue playback and audio qualification remain
  open; no alpha.4 OTA is authorized during the alpha.2 endurance run.
