# Canary baseline `hal.8-alpha.2`

## Build

- ESPHome: `2025.10.5`, pinned Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,848,416` bytes, 90.9% of the OTA partition
- Application flash: `1,848,022` bytes, 91.0%
- RAM: `39,100` bytes, 11.9%
- MD5: `a3b5830fc5b851544e2fb2c218ec40f5`
- SHA-256: `3b7935b68bcaa43b4cbbe4f63b3287f4d2cbc77e4bc0dd007647ba7ee5ace017`

## Calibration architecture

Wake-word model, component ID and sensitivity thresholds are substitutions
shared by the production Okay Hal and calibration-only Okay Nabu builds. The
change has no RAM or flash-size cost relative to `hal.8-alpha.1`.

The clean Nabu build is 1,843,424 OTA bytes (90.7%) and uses 39,036 RAM bytes.
It uses a distinct node identity and omits the production HTTP update entity,
preventing an accidental cross-profile update. It has not been flashed to the
canary.

## Canary validation

- OTA deployment to `10.10.40.100`: passed on 2026-07-21.
- Reported version: `2025.3.1-hal.8-alpha.2`.
- Post-flash software reboot: passed, back to `waiting` in 17.65 seconds.
- Injected timeout: passed with one timeout, one recovery,
  `last_recovery_reason=voice_timeout`, then `healthy` and `waiting`.

## Required before promotion

- One hundred announcement/TTS cycles total.
- Twenty-four hours of idle endurance.
- Physical power, Wi-Fi, wake-word, volume, mute and jack qualification.
- Consented Hal/Nabu day/night calibration measurements.

`hal.6` remains the published rollback image.
