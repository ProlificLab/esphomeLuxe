# Baseline hal.6

This is the recovery reference captured before the hal.7 state-machine work.

## Identity

- Project version: `2025.3.1-hal.6`
- Git commit: `6f5b3a9` plus CI-only commit `63c89e7`
- OTA artifact: `artifacts/muse-luxe-2025.3.1-hal.6.ota.bin`
- SHA-256: `8a8350fa93293ef8421f4c84004c4804a2969ae6d50697a72e104ba85d4db0d6`
- MD5: `cedf966640caccbabba098bcf22f7645`
- Flash use: `1,947,750 / 2,031,616 bytes (95.9%)`
- Canonical USB factory SHA-256:
  `16ad19ae504dae9e75d6be0cb72b6ada34bf932fae0f972a89b5230dc20c01ac`
- USB provenance: `docs/hal6-usb-recovery-manifest.json`

The production artifact is intentionally ignored by Git because it embeds
device secrets. Keep a private copy together with the matching local update
manifest.

## Observed healthy state

- Encrypted ESPHome API connected to Home Assistant.
- CPU frequency: 240 MHz.
- Free heap: approximately 184 KB.
- Largest free heap block: approximately 110 KB.
- Free PSRAM: approximately 4.13 MB.
- Wi-Fi signal during validation: approximately -25 dBm.
- Piper TTS playback completed successfully.
- A 55-second post-TTS observation showed no errors, warnings, or ring-buffer
  resets.

## Recovery

1. Publish the archived OTA artifact and its matching manifest to Home
   Assistant's private `/local/muse-luxe/` directory.
2. Use the firmware update entity when the ESPHome API is available.
3. If OTA is unavailable, validate the provenance and canonical factory image,
   flash it by USB, then restore the API encryption key with
   `scripts/configure_home_assistant_encryption.py`.
4. Verify wake word, TTS, media playback, center button, volume buttons, jack
   routing, diagnostics, and the three-second siren intent.
