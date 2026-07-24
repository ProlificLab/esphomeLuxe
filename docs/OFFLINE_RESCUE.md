# Offline microSD rescue audio

`hal.9.0-alpha.3` adds an opt-in rescue mode that does not require Wi-Fi, Home
Assistant, STT or an LLM. The implementation uses the Muse Luxe SPI wiring
documented by Raspiaudio: CS 13, CLK 14, MOSI 15 and MISO 2. It never writes to
or formats the card.

## Trust boundary

The firmware contains a minimal read-only SD-SPI and FAT16/32 reader. It can
open only the `RESCUE` directory and these canonical 8.3 files:

| File | Purpose |
| --- | --- |
| `READY.WAV` | Physical controls and mode confirmation |
| `POWER.WAV` | Short power-outage guidance |
| `PWRLIST.WAV` | Power-outage checklist |
| `EVAC.WAV` | Short evacuation guidance |
| `EVACLIST.WAV` | Evacuation checklist |
| `ALLCLEAR.WAV` | Conditional end-of-emergency reminder |

Files must be canonical WAV, PCM signed 16-bit little-endian, 48 kHz, stereo
and no longer than 180 seconds. There is no arbitrary filename, URL, write,
delete or format action. The Home Assistant rescue switch is internal and
there are no HA playback buttons, so Assist cannot trigger these messages.

## Prepare a card

1. Format a microSD card as FAT32 with an MBR partition table and volume label
   `MUSE_RESCUE`. Verify the selected device carefully before formatting.
2. Record and review all six messages with the family. The generic French text
   in `rescue-media/prompts.fr.yaml` is a starting point, not an emergency plan.
3. Convert each reviewed recording, for example:

```bash
ffmpeg -i reviewed-recording.wav -ar 48000 -ac 2 \
  -c:a pcm_s16le READY.WAV
```

4. Put all six fixed filenames in one source directory, then initialize and
   synchronize the mounted card:

```bash
python3 scripts/prepare_rescue_media.py \
  --source /path/to/reviewed-wav \
  --destination /Volumes/MUSE_RESCUE \
  --initialize
```

Later updates omit `--initialize`. The preparer refuses an unmarked card or a
volume with another name, rejects symlinks and invalid audio, copies atomically,
and writes `RESCUE/manifest.json` with SHA-256 values. It does not delete stale
files; the firmware ignores every non-allowlisted name.

## Physical controls

- Four short presses enter or exit rescue mode. The LED pulses bright orange.
- One short press plays the next item in the bounded five-message sequence.
- Two short presses stop local playback.
- Three short presses play `EVAC.WAV` directly.
- The volume buttons remain available.
- Long press still enables privacy. Privacy has priority over rescue mode.

The mode survives a reboot. Reconnecting Home Assistant does not exit it. Card
mount is retried on every physical entry, allowing insertion after boot.

## Validation and rollback

Static and card-preparation tests:

```bash
python3 scripts/check_offline_rescue_safety.py
python3 scripts/test_offline_rescue_safety.py
python3 scripts/test_prepare_rescue_media.py
```

Before promotion, test all six files on the physical canary, remove HA/network
access during playback, verify stop/exit/privacy/reboot behavior, and inspect
`Rescue Media Status` plus `Rescue Media Errors`. Remove the card and restore
`hal.9.0-alpha.2` to roll back; card contents are never modified by firmware.

Copy `docs/offline-rescue-record.example.json` into the ignored release
directory before testing. Record all fifteen scenarios, the six playback
counts and the card-manifest hash before and after the session. Both stable
gates, `emergency_offline` and `offline_rescue_physical`, must bind this exact
same record. Validate it explicitly:

```bash
python3 scripts/check_offline_rescue_evidence.py \
  release/offline-rescue-VERSION.json \
  --expected-version "VERSION" \
  --expected-firmware-sha256 "$(sha256sum release/muse-luxe-VERSION.ota.bin | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum packages/offline_rescue.yaml | cut -d' ' -f1)" \
  --expected-component-sha256 "$(sha256sum components/offline_media/offline_media.cpp | cut -d' ' -f1)"
```

Stable promotion recalculates the source hashes and verifies the candidate OTA.
The example remains failed and cannot serve as physical evidence.

## Hardware evidence

- [Raspiaudio Muse Luxe original firmware](https://github.com/RASPIAUDIO/Simple_Bluetooth_Speaker_ESP32)
- [Raspiaudio Muse library Luxe audio example](https://github.com/RASPIAUDIO/Muse_library/blob/main/examples/LUXE/Audio_out/Audio_out.ino)
- [ESP-IDF SPI master API](https://docs.espressif.com/projects/esp-idf/en/v5.4.2/esp32/api-reference/peripherals/spi_master.html)
