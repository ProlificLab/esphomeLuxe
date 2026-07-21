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

Do not erase NVS, reset HA storage or overwrite unrelated Proxmox disks as a
first-line diagnostic action.
