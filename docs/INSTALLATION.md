# Installation

## Requirements

- Muse Luxe, data-capable USB cable and an 8 GB or larger recovery drive.
- Home Assistant with ESPHome, Wyoming/Piper and package loading enabled.
- Private `secrets.yaml` created from `secrets.example.yaml`.
- The retained exact `hal.6` OTA and, before rotation, a separately reviewed
  USB factory image that passes the closed recovery gate below.

## Canary workflow

1. Flash an upstream factory image over USB only for initial provisioning. Do
   not call it an exact `hal.6` rollback unless it passes the recovery gate.
2. Provision Wi-Fi through Improv Serial; do not embed household credentials in
   Git.
3. Compile with the pinned command in `README.md`.
4. Upload only to one canary with ESPHome OTA.
5. Run configuration, size, reboot, timeout, privacy and TTS tests.
6. Publish HA packages with `publish_ha_file.sh`, run `ha core check`, then
   restart HA.
7. Keep every opt-in alert disabled until its synthetic and physical tests pass.

Never point the production update entity at an alpha manifest.

The device's HTTP update entity currently reads the private root
`/local/muse-luxe/manifest.json`. That root remains the `hal.6` recovery
reference, so publishing a development manifest deliberately does not trigger
an update. After the 24-hour summary exists and the candidate SHA-256 has been
reviewed, install the exact artifact directly with:

```bash
uv run --with aioesphomeapi --with pyyaml scripts/install_canary_ota.sh \
  release/muse-luxe-VERSION.ota.bin \
  release/manifest-development.json \
  release/hal9-endurance-24h-final.summary.json \
  REVIEWED_SHA256 10.10.40.100
```

The command repeats the publication preflight, refuses a dirty worktree,
requires typing `INSTALL CANARY VERSION SHA256`, and mounts only the reviewed
artifact and secrets read-only into the pinned ESPHome container. It invokes
`espota2` on that exact file rather than recompiling. After the OTA reboot it
uses the encrypted API to require the exact version, `voice_state=waiting`,
`voice_health=healthy` and no voice error. `uv` creates the same isolated
runtime used by the other physical API tests; no global Python packages are
required.

If post-boot verification fails, do not repeat the canary flash automatically.
Collect diagnostics first. To restore the separately retained `hal.6` binary,
use its independently recorded SHA-256:

```bash
uv run --with aioesphomeapi --with pyyaml scripts/rollback_hal6_ota.sh \
  /private/path/muse-luxe-hal6.ota.bin REVIEWED_HAL6_SHA256 10.10.40.100
```

Rollback has its own confirmation, verifies SHA-256 plus the immutable root
manifest MD5/version, and first requires all three active credentials to match
the immutable `hal.6` domain. Only then does it upload and verify the encrypted
API after reboot. After credential rotation this check intentionally fails
before confirmation or upload: restore immutable `hal.6` over USB instead.
Never weaken authentication or retain/reuse the retired OTA password.

## Exact hal.6 USB recovery gate

An ESPHome factory image is not interchangeable with its OTA application. The
canonical Muse image contains the reviewed immutable `hal.6` OTA byte for byte
at offset `0x10000`, with no trailing payload. Its source commits, pinned
container, offsets, sizes and hashes are closed in
`docs/hal6-usb-recovery-manifest.json`.

The canonical image is composed without reading or reconstructing credentials.
Use only the reviewed 64 KiB prefix from the pinned historical build and the
exact retained OTA; the command is atomic, private and refuses overwrite:

```bash
python3 scripts/compose_hal6_usb_recovery.py \
  /private/path/muse-luxe-2025.3.1-hal.6.ota.bin \
  /private/path/pinned-hal6-donor.factory.bin \
  /private/path/muse-luxe-2025.3.1-hal.6.factory.bin \
  --manifest manifest_update.json
```

Validate the provenance record and the resulting private image before placing
it on recovery media:

```bash
python3 scripts/check_hal6_recovery_manifest.py
python3 scripts/check_hal6_usb_recovery.py \
  /private/path/muse-luxe-2025.3.1-hal.6.ota.bin \
  /private/path/muse-luxe-2025.3.1-hal.6.factory.bin \
  --manifest manifest_update.json
```

The canonical factory SHA-256 is
`16ad19ae504dae9e75d6be0cb72b6ada34bf932fae0f972a89b5230dc20c01ac`.
A generic upstream image, a complete rebuild made with example credentials, a
symlink, an altered boot prefix, a wrong offset or extra bytes fails. Do not
flash a failed image and do not derive or reuse retired credentials from a
firmware binary.

The authenticated OTA rollback is available only when
`HAL6_REFERENCE_SECRETS` names a separately retained, current-user-private
`0600` file containing the real immutable `hal.6` domain. Public example
credentials are always rejected. If that reference is absent, use only a USB
factory image that has passed the gate above.

For physical recovery, disconnect other serial ESP devices, place the Muse in
USB boot mode and identify its exact `/dev/cu.*` port. Then run:

```bash
scripts/flash_hal6_usb.sh \
  /private/path/muse-luxe-2025.3.1-hal.6.ota.bin \
  /private/path/muse-luxe-2025.3.1-hal.6.factory.bin \
  /dev/cu.EXACT_MUSE_PORT
```

The script repeats both gates around the literal confirmation and pins
`esptool==5.3.1`. It does not use `--force`, erase the full 4 MB flash, read a
second secret-bearing copy back to disk, or contact the network. Esptool's
normal post-write verification must succeed. Reprovision Wi-Fi afterward and
restore the encrypted Home Assistant API entry. Never run this command merely
to test it on a healthy canary.

Before any beta or stable promotion, follow `docs/RELEASES.md` and complete a
copy of `docs/qualification-record.example.json` in the ignored `release/`
directory. The promotion command performs a second clean build and refuses any
commit, hash, compatibility or gate mismatch; do not bypass it by copying a
firmware file directly into a channel directory.

## Music Assistant

Use the stable Home Assistant app, not beta or nightly. After completing its
local account setup, confirm only the Supervisor-discovered Home Assistant
integration flow with `scripts/confirm_music_assistant_integration.py`. The
script refuses manual and OAuth flows so no HA password or long-lived token is
stored in the repository.

Add only explicitly selected Home Assistant players to the Music Assistant
player provider. For the current canary, the allowlist contains only
`media_player.raspiaudio_muse_luxe`. Publish
`home-assistant/packages/muse_music_assistant.yaml`, validate the HA
configuration, and restart HA before running the end-to-end test described in
`docs/MUSIC_ASSISTANT.md`.

## Interactive routines

Publish the package and French sentence file using the closed destination roots
shown in `docs/INTERACTIVE_ROUTINES.md`. Run `ha core check` before restarting,
then run `scripts/test_home_assistant_routines.py` inside HA Core. Keep
`input_boolean.muse_routines_enabled` off until household wording and physical
sensor coverage have been reviewed.

## Family intercom

Follow `docs/INTERCOM.md` to publish the deterministic package, French intents
and non-audio lifecycle test. Keep `input_boolean.muse_intercom_enabled` off
until two distinct satellites pass the bidirectional carillon, LED, timeout,
restart and transcript-retention gates. The current fixed call origin is the
`bureau`; do not present it as room-aware until the trusted satellite-origin
hook has been implemented.

## Deferred family messages

After the firmware endurance run, follow `docs/FAMILY_MESSAGES.md` and run
`scripts/provision_family_messages.sh`. Inspect the legacy one-slot flag before
requesting the maintenance restart. After restart, run the non-audio lifecycle
test before queuing any real family transcript.

## Proxmox read-only monitoring

Follow `docs/PROXMOX_READONLY.md` to publish the two in-HA helpers and run
`scripts/provision_proxmox_readonly.sh`. Keep the role at `PVEAuditor`; the
provisioner must report only `.Audit` permissions and all generated control
buttons disabled before deploying the updated house-intelligence package.

## OPNsense read-only monitoring

Run `PVE_HOST=root@192.168.1.10 scripts/provision_opnsense_readonly.sh` after
OPNsense and Home Assistant are reachable. It backs up OPNsense, installs the
GET-only gateway endpoint, stores credentials outside Git, validates HA and
proves unrelated API and POST denial. The security boundary and rollback are
documented in `docs/OPNSENSE_READONLY.md`.

## Frigate authenticated monitoring

Run `PVE_HOST=root@192.168.1.10 scripts/provision_frigate_readonly.sh` to create
the dedicated Frigate viewer, install the checksum-pinned official integration
and enforce the Home Assistant registry policy. The procedure deliberately
uses authenticated port `8971`, disables all Frigate control domains and hides
raw entities from Assist. Follow `docs/FRIGATE_READONLY.md` for validation and
credential rotation; do not substitute Frigate's internal port `5000`.

## Authenticated video review

After the firmware endurance run, follow `docs/VIDEO_REVIEW.md` and run
`scripts/provision_video_review_dashboard.sh`. The command validates but does
not restart HA by default. Keep review off and its destination disabled until
the closed camera map, image freshness and five-minute expiry pass physically.

## Local interpreter

Follow `docs/INTERPRETER.md`, then run
`PVE_HOST=root@192.168.1.10 scripts/provision_interpreter.sh`. Deploy the
`hal.9.0-alpha.2` canary firmware before enabling the package in daily use, as
the package requires its context-reset API action. Keep the interpreter alpha
and opt-in until bilingual microphone and pronunciation tests pass.

## Local acoustic guardian

Follow `docs/ACOUSTIC_GUARDIAN.md` to inventory, consent, probe and prepare one
camera at a time. The repository policy is disabled and the generator writes a
separate private candidate; it never edits or restarts Frigate. Do not apply a
candidate until the one-day retention tradeoff and room consent are reviewed.

## Physical modes gate

After the active endurance run and the reviewed canary OTA, follow
`docs/MODES.md`. The transactional API test requires the exact firmware version
and a new evidence path, restores privacy and continuous-conversation state on
failure, and emits JSON only after verified cleanup. Complete the separate
button, audio and LED observation record before marking `physical_controls`.
Use the closed record and validator in `docs/PHYSICAL_CONTROLS.md`; promotion
will reject an unbound note or a record for another OTA.

## Offline rescue card

Follow `docs/OFFLINE_RESCUE.md` to review the six messages, format a dedicated
FAT32/MBR card named `MUSE_RESCUE`, validate the WAV files and synchronize them
with `scripts/prepare_rescue_media.py`. Do not deploy `hal.9.0-alpha.5` before
the alpha 2 endurance gate and physical canary qualification are complete.
