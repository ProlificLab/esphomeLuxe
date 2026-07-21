# Raspiaudio Muse Luxe Voice Satellite

[![Video Guide](https://img.youtube.com/vi/iLQuCf8FqXM/0.jpg)](https://www.youtube.com/watch?v=iLQuCf8FqXM)

Welcome to the Raspiaudio Muse Luxe Voice Satellite project! This guide will help you get started with your device, including setup instructions, source code information, and support options.

## ProlificLab stability variant

The `codex/muse-luxe-hal-stability` branch carries a small experimental set of
changes for a locally managed Muse Luxe:

- adds the community microWakeWord V2 model for "Okay Hal" and keeps Okay Nabu
  in a separate calibration-only image;
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

Operational documentation:

- [Installation and canary workflow](docs/INSTALLATION.md)
- [Diagnosis and rollback](docs/OPERATIONS.md)
- [Privacy and safety contract](docs/PRIVACY.md)
- [Development, beta and stable channels](docs/RELEASES.md)

Wake-word A/B testing uses the isolated Okay Nabu configuration and protocol in
[`docs/calibration.md`](docs/calibration.md); it is never part of the primary
firmware manifest.

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
release directory contains a versioned OTA image, MD5/SHA-256 files, a
channel-specific manifest, build metadata, section sizes and the 120 largest
symbols. CI emits only `development`; beta/stable promotion requires a reviewed
qualification record and explicit command documented in `docs/RELEASES.md`.

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

Home Assistant restart recovery and unattended idle endurance have dedicated
harnesses. The latter defaults to 24 hours and appends machine-readable JSONL:

```bash
docker run --rm --network host --entrypoint python \
  -v "$PWD":/config -v "$HOME/.ssh":/root/.ssh:ro -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  scripts/test_ha_restarts.py --pve-host user@proxmox-host --cycles 10
docker run --rm --network host --entrypoint python \
  -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  scripts/monitor_endurance.py
```

The timeout path can be exercised without waiting 45 seconds. Its Home
Assistant button is diagnostic and disabled by default:

```bash
docker run --rm --network host --entrypoint python \
  -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  scripts/test_timeout_injection.py
```

### Home Assistant package

`home-assistant/packages/muse_luxe.yaml` provides queued and urgent Piper TTS,
day/night volumes, whole-home targeting and bounded privacy wrappers. Publish
it, enable package loading once, validate the configuration and restart HA:

```bash
PVE_HOST=user@proxmox-host HA_DESTINATION_ROOT=/config/packages \
  scripts/publish_ha_file.sh home-assistant/packages/muse_luxe.yaml muse_luxe.yaml
PVE_HOST=user@proxmox-host RESTART_HA=1 scripts/enable_ha_packages.sh
```

`hal.9.0-alpha.1` also adds named-timer telemetry and a local completion sound,
a five-minute bounded continuous conversation, and deterministic center-button
gestures: single click toggles audio mute, double click stops, long press toggles
privacy, and triple click toggles continuous conversation. Privacy is restored
after reboot; only a hardware microphone power cut can provide a strong physical
privacy guarantee.

Canary mode and privacy-persistence tests use the encrypted ESPHome API:

```bash
uv run --with aioesphomeapi --with pyyaml scripts/test_hal9_modes.py
uv run --with aioesphomeapi --with pyyaml scripts/test_privacy_reboot.py
```

The same HA package contains the first `hal.9.1` communication layer. A
transcribed push-to-talk message always starts with an audible chime. Family
messages are delivered immediately when the selected `person` is home, or one
message is retained locally until presence, explicit forced delivery, or
expiry. A second request is rejected instead of silently replacing the pending
message.

This alpha intentionally does not claim live room-to-room audio or playback
transfer: both need a second satellite, and playback transfer additionally
needs Music Assistant, which is not currently installed on the target HA
instance.

`home-assistant/packages/muse_house_intelligence.yaml` starts the read-only
`hal.9.2` layer. It exposes a normalized energy state with raw Victron facts,
source timestamps and a three-minute stale-data guard. The narration script
only reads sensors; no Victron `number`, `select`, `switch` or `button` is
called. Low/critical battery announcements are local and deterministic but
remain disabled until `input_boolean.muse_energy_alerts_enabled` is explicitly
enabled after reviewing the two thresholds.

Frigate's MQTT event path can be enabled with a dedicated random broker login:

```bash
PVE_HOST=root@proxmox-host scripts/configure_frigate_mqtt.sh
```

The script keeps dated VM backups and stores the credential only in Frigate's
root-only `.env` and Mosquitto options. `muse_video_alerts.yaml` then provides
opt-in person announcements with camera allowlisting, confidence threshold,
event-ID deduplication, cooldown and night-mode suppression. It never identifies
a person or changes camera/alarm state. The optional richer Frigate integration
still follows the [official HACS installation guide](https://docs.frigate.video/integrations/home-assistant).

`muse_acoustic_guardian.yaml` prepares the first `hal.9.3` experiment without
enabling any camera microphone. It is opt-in, starts with an empty camera
allowlist, listens only for `fire_alarm` by default, rate-limits announcements
and asks for human/sensor verification. It cannot trigger a siren or another
critical action. Real audio detection must be enabled separately per consented
Frigate camera after checking that stream's audio role and retention policy.

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
