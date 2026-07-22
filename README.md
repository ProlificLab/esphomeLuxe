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
- exposes reset, heap, PSRAM, loop-time, uptime, Wi-Fi, and last voice-error
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
- [Machine-verifiable qualification record](docs/qualification-record.example.json)
- [Read-only OPNsense telemetry](docs/OPNSENSE_READONLY.md)
- [Authenticated Frigate camera telemetry](docs/FRIGATE_READONLY.md)
- [Local bounded French-English interpreter](docs/INTERPRETER.md)
- [Audible, bounded family intercom](docs/INTERCOM.md)
- [Offline microSD rescue audio](docs/OFFLINE_RESCUE.md)

Wake-word A/B testing uses the isolated Okay Nabu configuration and protocol in
[`docs/calibration.md`](docs/calibration.md); it is never part of the primary
firmware manifest.

The main configuration is intentionally small and composes the eight files in
`packages/`: hardware, audio, voice, UI, recovery, diagnostics, updates and
offline rescue.

The primary image compiles logs at `ERROR` to stay below the 93% OTA target.
For USB diagnosis, `luxe_microWW_diagnostic.yaml` keeps `WARN` logs, uses a
distinct node identity and deliberately omits the HTTP update component so it
cannot enter a normal release channel.

Build that troubleshooting image only when a USB serial investigation is
needed:

```bash
docker run --rm -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  compile luxe_microWW_diagnostic.yaml
```

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
version="2025.3.1-hal.9.0-alpha.5"
artifact="release/muse-luxe-$version.ota.bin"
PVE_HOST=user@proxmox-host scripts/deploy_local_update.sh \
  "$artifact" \
  release/manifest-development.json \
  release/hal9-endurance-24h-final.jsonl.summary.json \
  "$(sha256sum "$artifact" | cut -d' ' -f1)"
```

Publication is refused unless the worktree is clean and the reviewed SHA-256,
manifest and successful 24-hour endurance summary all identify the same exact
version. Firmware is uploaded before the private `development` manifest. The
root `hal.6` manifest is not changed and this command does not trigger an OTA.

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

Optional timer checkpoints are isolated in
`home-assistant/packages/muse_timer_coach.yaml`. They are disabled by default,
never replay a missed checkpoint after reconnect and use the existing bounded
announcement queue. Publish and validate both required packages without a
default restart with:

```bash
PVE_HOST=user@proxmox-host scripts/provision_timer_coach.sh
```

See `docs/TIMER_COACH.md` for the physical pause/resume, reconnect, night-mode
and audio-contention qualification gates.

`hal.9.0-alpha.5` and `hal.9.0-ha-alpha.3` add bounded day/night brightness to
the existing Muse LED without moving color or effect ownership out of the
firmware state machine. Timer ticks retain the selected brightness. See
`docs/NIGHT_LED.md` for the profile table, paired deployment and rollback gate.

The post-endurance mode gate uses a version-bound, transactional evidence
writer. Follow `docs/MODES.md`; a passing API JSON never substitutes for the
separate physical button, audio and LED observations. Those observations use
the OTA-bound closed record in `docs/PHYSICAL_CONTROLS.md` rather than free-form
release notes.

Canary mode and privacy-persistence tests use the encrypted ESPHome API:

```bash
uv run --with aioesphomeapi --with pyyaml scripts/test_hal9_modes.py
uv run --with aioesphomeapi --with pyyaml scripts/test_privacy_reboot.py
```

The `hal.9.1` communication layer always prefixes a transcribed push-to-talk
message with an audible chime. `hal.9.1-ha-alpha.4` expands deferred delivery to
three persistent 240-character slots with FIFO ordering, expiry and strict full
queue refusal. A delivery interrupted by HA is quarantined for explicit retry
or discard and is never replayed automatically. Migration, provisioning and
physical gates are documented in `docs/FAMILY_MESSAGES.md`.

Music Assistant `2.9.9` stable is installed on the target HA instance. The
allowlisted Muse is exposed as `media_player.raspiaudio_muse_luxe_2`; guarded
local announcements and an opt-in manual queue-transfer script are provided by
`home-assistant/packages/muse_music_assistant.yaml`. `hal.9.1-ha-alpha.5` also
adds two-to-four-player temporary groups with a restorable timer, relative-volume
restoration and explicit crash recovery. Live room-to-room audio and
multi-player transfer remain unvalidated until a second satellite is deployed;
see `docs/MUSIC_ASSISTANT.md` for the physical gates.

`home-assistant/packages/muse_house_intelligence.yaml` starts the read-only
`hal.9.2` layer. It exposes a normalized energy state with raw Victron facts,
source timestamps and a connection-plus-five-minute telemetry freshness guard.
The narration script
only reads sensors; no Victron `number`, `select`, `switch` or `button` is
called. Low/critical battery announcements are local and deterministic but
remain disabled until `input_boolean.muse_energy_alerts_enabled` is explicitly
enabled after reviewing the two thresholds.

`home-assistant/packages/muse_interactive_routines.yaml` adds persisted,
guidance-only departure, bedtime, server, outage, alarm and evacuation
checklists. Local French commands, manual-versus-sensor proof, pause/resume and
the deployment test are documented in `docs/INTERACTIVE_ROUTINES.md`. The
feature remains opt-in and cannot invoke critical infrastructure actions.

The same read-only layer now consumes the official Proxmox VE integration
through a dedicated privilege-separated `PVEAuditor` token. All generated
control buttons are disabled, no Proxmox entity is exposed to Assist, and the
combined energy/server narrator uses five-minute freshness guards. Provisioning,
rotation and validation are documented in `docs/PROXMOX_READONLY.md`.

Frigate's MQTT event path can be enabled with a dedicated random broker login:

```bash
PVE_HOST=root@proxmox-host scripts/configure_frigate_mqtt.sh
```

The script keeps dated VM backups and stores the credential only in Frigate's
root-only `.env` and Mosquitto options. `muse_video_alerts.yaml` then provides
opt-in person announcements with camera allowlisting, confidence threshold,
event-ID deduplication, cooldown and night-mode suppression. It never identifies
a person or changes camera/alarm state. The official Frigate integration is
pinned and provisioned on authenticated port `8971` with a dedicated `viewer`
account. All generated controls are disabled, raw entities are hidden from
Assist, and only the normalized camera health sensor is exposed. Provisioning,
validation, rotation and rollback are documented in
`docs/FRIGATE_READONLY.md`.

`hal.9.2-ha-alpha.6` adds an optional authenticated image-review dashboard for
the two explicitly mapped entrance cameras. It shows only a fresh existing HA
person image entity for five minutes, stores no image or token and creates no
public Frigate notification URL. No mobile app is currently enrolled, so phone
delivery remains honestly unavailable. Provisioning, qualification and
rollback are documented in `docs/VIDEO_REVIEW.md`.

`muse_acoustic_guardian.yaml` prepares the first `hal.9.3` experiment without
enabling any camera microphone. It is opt-in, starts with an empty camera
allowlist, listens only for `fire_alarm` by default, rate-limits announcements
and records optional dedicated-sensor corroboration. It returns to off after a
Home Assistant restart and cannot trigger a siren or another critical action.
The consent-bound candidate generator enforces local go2rtc input, closed
labels, high thresholds, disabled transcription and one-day retention before a
real Frigate camera can be considered. Follow `docs/ACOUSTIC_GUARDIAN.md`;
there is intentionally no automatic apply command.

`muse_interpreter.yaml` adds the second `hal.9.3` experiment: two local,
tool-free French-English pipelines with a ten-minute session, explicit
direction, physical/privacy/timeout exits and deterministic restoration. The
firmware clears its conversation identifier on every exit so interpreter text
cannot flow into a later house request. Provisioning and rollback are described
in `docs/INTERPRETER.md`.

`hal.9.0-alpha.3` adds a source-qualified, physical-only rescue mode backed by
the verified Muse Luxe microSD bus. A minimal read-only FAT reader accepts six
fixed, bounded WAV files and no arbitrary media or card writes. It remains
undeployed while the alpha 2 endurance trace and physical card gates run; see
`docs/OFFLINE_RESCUE.md`.

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
The tested stable setup and recovery behavior are documented in
`docs/MUSIC_ASSISTANT.md`. The Home Assistant player provider is restricted to
the Muse and uses `announce_volume_strategy=none`; the HA package sets and
restores announcement volume because this ESPHome player cannot do that
natively through Music Assistant.


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
