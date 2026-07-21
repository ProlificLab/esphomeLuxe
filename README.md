# Raspiaudio Muse Luxe Voice Satellite

[![Video Guide](https://img.youtube.com/vi/iLQuCf8FqXM/0.jpg)](https://www.youtube.com/watch?v=iLQuCf8FqXM)

Welcome to the Raspiaudio Muse Luxe Voice Satellite project! This guide will help you get started with your device, including setup instructions, source code information, and support options.

## ProlificLab stability variant

The `codex/muse-luxe-hal-stability` branch carries a small experimental set of
changes for a locally managed Muse Luxe:

- adds the community microWakeWord V2 model for "Okay Hal" while retaining
  Okay Nabu as the recovery wake word;
- reduces runtime logging to preserve ESP32 inference headroom;
- increases the speaker buffer from 100 ms to 300 ms to tolerate short network
  and TTS delivery stalls;
- restores the microphone and wake-word engine after a voice-pipeline error;
- aborts and recovers voice exchanges that remain stuck for 45 seconds;
- runs the ESP32 at 240 MHz and keeps only Okay Hal plus Okay Nabu to preserve
  inference and flash headroom;
- exposes reset, heap, PSRAM, loop-time, CPU, uptime, Wi-Fi, and last voice-error
  diagnostics to Home Assistant;
- protects the native API and OTA endpoint with local secrets;
- corrects invalid low-voltage battery readings instead of reporting 100%.

The upstream source commit and community model URL are pinned for reproducible
builds. The community model repository does not currently declare a license,
so the model is referenced rather than redistributed and this branch should be
treated as a private evaluation build. The original Raspiaudio firmware remains
the recovery path.

The complete technical and product program is maintained in
[ROADMAP.md](ROADMAP.md).

The main configuration is intentionally small and composes the seven files in
`packages/`: hardware, audio, voice, UI, recovery, diagnostics and updates.

### Private build and local updates

Copy `secrets.example.yaml` to the ignored `secrets.yaml`, replace all values,
then compile with the pinned ESPHome image:

```bash
docker run --rm -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  compile luxe_microWW.yaml
```

Production binaries contain device secrets and must not be attached to a public
GitHub release. Publish them to Home Assistant's local web directory instead:

```bash
PVE_HOST=user@proxmox-host scripts/deploy_local_update.sh
```

The firmware updater reads this LAN-only manifest. GitHub Actions compiles with
non-production example secrets to validate every branch and pull request; tags
create source-only releases.

Every CI build also runs `scripts/check_firmware_size.sh`,
`scripts/report_firmware_symbols.sh` and `scripts/package_firmware.sh`. The
release directory contains a versioned OTA image, MD5/SHA-256 files, the
matching manifest, the section sizes and the 120 largest symbols.

Canary reboot recovery can be exercised from the pinned ESPHome container:

```bash
docker run --rm --entrypoint python -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  scripts/test_reboots.py --cycles 3
```

Repeated announcement recovery can be tested after publishing the WAV through
Home Assistant:

```bash
PVE_HOST=user@proxmox-host scripts/publish_ha_file.sh \
  wav/sounds_timer_finished.wav muse-luxe/test-audio.wav
docker run --rm --entrypoint python -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  scripts/test_audio_endurance.py --cycles 10
```

## Introducing the New Version: luxe_microWW

Discover the enhancements in the latest release!

### Features:

- **Micro Wake Word**: The primary image uses "Okay Hal"; alternate wake-word
  models are kept in separate calibration builds to preserve OTA headroom.
- **Full interface with Home Assistant Assist**
- **MP3/AAC player**: Media Browser, My media,...

### Flashing Your Device

1. Open **Google Chrome**.
2. Navigate to [apps.raspiaudio.com](https://apps.raspiaudio.com).
3. Choose **Muse Luxe - Home Assistant** and follow the on-screen instructions for flashing and initialize your WiFi credentials

  **an alternative method** for Wifi init is available
  1. Connect to the device's access point with these credentials:
   - **SSID**: Raspiaudio-Luxe
   - **Password**: 12345678 for the official build; the ProlificLab variant
     uses `fallback_ap_password` from the private `secrets.yaml`
  2. The private fork does not embed the captive-portal web UI. Provision Wi-Fi
     over USB with Improv Serial; the fallback AP keeps OTA recovery available
     at `192.168.4.1`.
### Interface
**Led**
1. Blue => waiting Wake Word
2. Green => Listening
3. Yellow => Answering
4. Orange => External player
   
**Buttons**
1. Plus => volume up
2. Minus => volume down
3. Center
- click => mute/unmute
- double click => stop external player
     
   
### Music Assistant
If you want to use it in good conditions you will have to change one parameter in Music Assistant.
1. Select your player's parameters (Raspiaudio Muse Luxe)
2. Select Open Settings => Avanced settings => Output codec to use for streaming audio to the player
3. There choose .wav
4. Save


### Source Code

Explore the [ProlificLab fork](https://github.com/ProlificLab/esphomeLuxe) and
the [Raspiaudio upstream repository](https://github.com/RASPIAUDIO/esphomeLuxe).
For recompilation, perform a full ESPHome build clean first.

### Forum & Support

Join our community for discussions and support: [Raspiaudio Forum Thread](https://forum.raspiaudio.com/t/muse-luxe-voice-assistant-now-possible/726/209)

### Step-by-Step Video Guide

For a comprehensive walkthrough, watch our [Step-by-Step Video Guide](https://youtu.be/QDDjXAWuk0E).

We hope you enjoy using your Raspiaudio Muse Luxe Voice Satellite! For any further assistance, feel free to reach out via the forum.



## Firmware Update Procedure

1. Change the project version in the `.yaml` file.

2. Build the firmware. Locate:
   .esphome/build/raspiaudio-radio/.pioenvs/raspiaudio-radio/firmware.ota.bin
   Rename it to:
   update_firmware.bin

3. Compute checksum:
   md5sum update_firmware.bin

4. Edit manifest_update.json and replace the "md5" value with the result from step 3.
