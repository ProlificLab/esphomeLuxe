# Installation

## Requirements

- Muse Luxe, data-capable USB cable and an 8 GB or larger recovery drive.
- Home Assistant with ESPHome, Wyoming/Piper and package loading enabled.
- Private `secrets.yaml` created from `secrets.example.yaml`.
- A retained copy of the `hal.6` recovery images and checksums.

## Canary workflow

1. Flash the upstream/recovery factory image over USB if the device is not
   reachable.
2. Provision Wi-Fi through Improv Serial; do not embed household credentials in
   Git.
3. Compile with the pinned command in `README.md`.
4. Upload only to one canary with ESPHome OTA.
5. Run configuration, size, reboot, timeout, privacy and TTS tests.
6. Publish HA packages with `publish_ha_file.sh`, run `ha core check`, then
   restart HA.
7. Keep every opt-in alert disabled until its synthetic and physical tests pass.

Never point the production update entity at an alpha manifest.

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
