# hal.9.0-alpha.3 baseline

## Scope

- Minimal read-only SD-SPI transport on the official Muse Luxe pins.
- Minimal FAT16/32 parser restricted to `RESCUE` and six 8.3 WAV names.
- Local persistent rescue mode with physical entry, playback, stop and exit.
- Privacy precedence, no HA controls, no network dependency and no card writes.
- Guarded admin-side card preparation with format, duration and SHA-256 checks.

## Source qualification

- ESPHome 2025.10.5 configuration validation passed.
- Pinned clean compilation passed without OOM.
- Firmware uses 1,903,344 bytes, 93.6% of the 2,031,616-byte OTA partition.
- This is below the `hal.6` regression baseline of 1,948,144 bytes and the 97%
  hard limit, but above the 93% roadmap target; the warning remains open.
- Card-preparation unit tests and malicious static fixtures passed.
- A temporary 64 MB FAT32/MBR image named `MUSE_RESCUE` was initialized,
  synchronized, volume-verified and detached with all six checksums present.
- No OTA or development-channel publication was performed during the running
  `hal.9.0-alpha.2` endurance trace.

## Open hardware gates

- Prepare a reviewed six-file FAT32 card and verify detection plus every clip.
- Simulate total HA/network loss during playback.
- Verify single/double/triple/quadruple gestures, privacy priority and volume.
- Verify rescue persistence across reboot and explicit physical exit afterward.
- Remove the card during idle and playback; require bounded failure and recovery.
- Repeat normal voice, interpreter, timeout and reboot regressions after OTA.
- Investigate the remaining 0.6 percentage-point size target warning before
  beta promotion; do not weaken the 97% hard limit.

## Rollback

Exit rescue mode, remove the microSD card and OTA `hal.9.0-alpha.2`. The card is
not part of firmware state and remains untouched. Production stays pinned to
the private `hal.6` recovery image.
