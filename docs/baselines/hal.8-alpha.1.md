# Canary baseline `hal.8-alpha.1`

## Build

- ESPHome: `2025.10.5`, pinned Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,848,416` bytes, 90.9% of the OTA partition
- Application flash: `1,848,022` bytes, 91.0%
- RAM: `39,100` bytes, 11.9%
- MD5: `2301781693e86f1bd34ed353b008a8af`
- SHA-256: `5b4ec0029f8fe0851bcdf3ec2ac29ea41dccab65b79d1aaef085d3c3c0554ab3`

The disabled-by-default timeout injection and its shared production recovery
path add only 432 OTA bytes over `hal.7-alpha.3`.

## Qualification tooling

- `test_ha_restarts.py` restarts HA through the Proxmox guest agent while
  measuring the encrypted ESPHome telemetry in parallel.
- `monitor_endurance.py` records timestamped JSONL evidence and gates final
  health, state, heap, PSRAM, voice errors and timeouts.
- A ten-second endurance smoke test passed with three samples, zero memory
  loss, zero new errors and zero new timeouts against `hal.7-alpha.3`.
- The final `hal.7-alpha.3` HA restart series passed eight measured cycles in
  8.07-8.76 seconds, 8.34 seconds average, with one reconnect per cycle.

## Canary validation

- OTA deployment to `10.10.40.100`: passed on 2026-07-21.
- Reported version: `2025.3.1-hal.8-alpha.1`.
- Injected timeout: passed; timeout and recovery counters each advanced once,
  `last_recovery_reason` became `voice_timeout`, then state returned to
  `healthy` and `waiting`.
- Post-flash software reboot: passed, back to `waiting` in 15.12 seconds.

## Required before promotion

- One hundred announcement/TTS cycles total.
- Twenty-four hours of idle endurance.
- Physical power, Wi-Fi, wake-word, volume, mute and jack qualification.

`hal.6` remains the published rollback image.
