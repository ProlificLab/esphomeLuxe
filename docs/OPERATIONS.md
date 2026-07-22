# Operations and recovery

## Daily diagnosis

Check firmware version, voice state/health, last error, last recovery reason,
heap, PSRAM, Wi-Fi, reset reason and HA/Frigate availability before rebooting.
Export timestamps and exact spoken phrase for reproducible voice failures.

## Recovery order

1. Stop continuous conversation and clear privacy only if intentionally desired.
2. Restart Home Assistant and confirm the Muse returns `offline -> waiting`.
3. Reboot the Muse and wait at least 60 seconds for Safe Mode health marking.
4. Use ESPHome Safe Mode OTA if the normal image loops.
5. Restore the private `hal.6` OTA artifact and matching manifest.
6. If networking is unavailable, USB-flash the archived factory recovery image.

## Proxmox monitoring credential

The Home Assistant Proxmox token is revocable independently of root. Rerun
`scripts/provision_proxmox_readonly.sh` to audit its ACL and disabled-button
state. For suspected exposure, use the revocation and explicit rotation
procedure in `docs/PROXMOX_READONLY.md`; never add power-management privileges
to make a button work.

## OPNsense telemetry credential

Run `scripts/test_opnsense_live.sh` to verify the GET-only endpoint, unrelated
API denial and non-GET rejection. If a major OPNsense upgrade removes the Muse
companion files, rerun `scripts/provision_opnsense_readonly.sh`; do not grant
the broader `System: Gateways` privilege as a shortcut. Timestamped
`/conf/config.xml.pre-muse-readonly-*` files provide configuration rollback.

## Frigate camera telemetry

Run `scripts/test_frigate_viewer.sh` to verify authenticated viewer access,
statistics access and administrator denial. Rerun
`scripts/provision_frigate_readonly.sh` to repair registry hardening after an
integration upgrade. An unavailable camera is a source/stream fault, not a
reason to grant `admin`, expose raw entities to Assist or use port `5000`.
Account revocation, database backups and component rollback are documented in
`docs/FRIGATE_READONLY.md`.

For acoustic detection, keep `input_boolean.muse_acoustic_guardian_enabled`
off while diagnosing camera streams. Follow `docs/ACOUSTIC_GUARDIAN.md`; never
extend retention, enable speech transcription or add a direct alarm action to
work around a missing MQTT event.

The `Revue video Muse` dashboard displays only a fresh existing HA image entity
while its five-minute timer is active. If the camera or event ID does not match
Frigate, close review rather than using the image for a decision. Recovery and
configuration rollback are in `docs/VIDEO_REVIEW.md`.

## Local interpreter recovery

Triple click, privacy mode and the ten-minute timer all terminate continuous
interpretation and restore the prior pipeline. If that fails, turn off
`switch.raspiaudio_muse_luxe_continuous_conversation`, call
`script.muse_stop_interpreter`, and verify the Voice Context Resets counter
increments. Remove the HA package before rolling firmware back below
`hal.9.0-alpha.2`; see `docs/INTERPRETER.md` for the full order.

## Offline rescue recovery

Four short presses exit rescue mode; two stop only the current local clip and a
long press still enforces privacy. If the card is absent or invalid, reinsert a
prepared card and enter again to remount it. Never reformat from firmware. For
rollback, physically exit, remove the card and restore `hal.9.0-alpha.2`; see
`docs/OFFLINE_RESCUE.md` for card validation and failure tests.

Do not erase NVS, reset HA storage or overwrite unrelated Proxmox disks as a
first-line diagnostic action.

## Verbose USB diagnosis

The primary `hal.9.0-alpha.4` image compiles only `ERROR` logs. Health, memory,
timeouts and recovery reasons remain available as API entities. When serial
WARN logs are required, compile and flash `luxe_microWW_diagnostic.yaml` over
USB. It identifies as `muse-luxe-diagnostic` and has no HTTP updater.

Treat that image as temporary: collect the serial trace, then restore the exact
qualified primary OTA or the published `hal.6` recovery image. Verify the node
name and project version after restoration; never promote the diagnostic image
to development, beta or stable.
