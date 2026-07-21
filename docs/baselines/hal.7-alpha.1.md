# Canary baseline `hal.7-alpha.1`

## Build

- ESPHome: `2025.10.5`, Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,923,600` bytes, 94.6% of the OTA partition
- RAM: `38,860` bytes, 11.9%
- MD5: `024db718ed5ed8fe56eb5d74fac47a0a`
- SHA-256: `d4688d626b813c89b9d5935670d337adaae3b16716bc08d0cab07464b34bb4cc`

## Canary validation

- OTA to `10.10.40.100`: passed on 2026-07-21.
- Encrypted ESPHome API handshake: passed in 94 ms.
- Reported project version: `2025.3.1-hal.7-alpha.1`.
- Central voice state after boot: `waiting`.
- Home Assistant Assist satellite state after boot: `idle`.
- `Last Voice Error`: empty after boot.

## Still required before promotion

- Ten ordinary power cycles.
- Ten Wi-Fi interruptions and recoveries.
- Ten Home Assistant restarts and recoveries.
- Voice, TTS, volume, mute, jack and timeout tests.
- Verify recovery to `waiting` in less than ten seconds after each injected error.

`hal.6` remains the published rollback image until every item above passes.
