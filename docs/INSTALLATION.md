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
