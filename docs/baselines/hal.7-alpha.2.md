# Canary baseline `hal.7-alpha.2`

## Build

- ESPHome: `2025.10.5`, Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,929,216` bytes, 94.9% of the OTA partition
- Application flash: `1,928,822` bytes, 94.9%
- RAM: `39,076` bytes, 11.9%
- MD5: `ea83237b6dca27d0aa23d3ddca5256b9`
- SHA-256: `160667695f3d4be0685817a8be3c808bac524fae09572240982c33567ba85c00`

## Added diagnostics

- Central voice state and synthetic health.
- Wake word, success, error, timeout, reconnect and recovery counters.
- Last recovery reason.
- Disabled-by-default normal restart and Safe Mode buttons.

Counters are session-only to avoid repeated writes to ESP32 flash.

## Software reboot campaign

Ten reboot requests were sent through the encrypted ESPHome API. The measured
returns to `waiting` were:

| Cycle | Result | Time |
| ---: | --- | ---: |
| 1 | pass | 16.82 s |
| 2 | pass | 15.98 s |
| 3 | pass | 19.63 s |
| 4 | pass | 19.55 s |
| 5 | pass | 17.09 s |
| 6 | pass | 16.51 s |
| 7 | pass | 16.11 s |
| 8 | pass | 16.50 s |
| 9 | slow recovery | between 20 and 60 s |
| 10 | pass | 16.10 s |

The slow cycle eventually reported `healthy`, `waiting` and reset reason
`Reboot request from api`. No cycle entered Safe Mode. This validates software
restart recovery, not physical power loss.

After the session-success accounting fix, the exact packaged binary passed an
additional smoke reboot in 16.91 seconds.

## Still required before promotion

- Ten physical power cycles.
- Ten Wi-Fi interruptions and recoveries.
- Ten Home Assistant restarts and recoveries.
- Voice, TTS, volume, mute, jack and forced-timeout tests.
- Explain or bound the occasional slow Home Assistant voice reconnection.

`hal.6` remains the published rollback image.
