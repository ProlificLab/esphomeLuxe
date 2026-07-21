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

Do not erase NVS, reset HA storage or overwrite unrelated Proxmox disks as a
first-line diagnostic action.
