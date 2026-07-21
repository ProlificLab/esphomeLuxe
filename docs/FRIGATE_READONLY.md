# Frigate authenticated camera telemetry

The Muse house narrator uses the official Frigate Home Assistant integration
without giving Assist or the conversational model camera controls. Home
Assistant connects to Frigate's authenticated port `8971` as the dedicated
`homeassistant_muse` user with the `viewer` role. Port `5000`, administrator
credentials and raw Frigate entities are outside this trust boundary.

## Provisioning

The provisioner creates or repairs the viewer account, stores its random
password in the macOS Keychain, downloads the pinned official integration,
verifies its SHA-256 digest, configures Home Assistant, disables generated
control entities and removes all raw Frigate entities from Assist:

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_frigate_readonly.sh
```

The password exists only in Keychain and the Home Assistant config entry. The
temporary password file is removed by the configuration helper. Rerunning the
command is idempotent unless the credential must be deliberately rotated.

## Validation

```bash
scripts/check_frigate_readonly.py
scripts/test_frigate_viewer.sh
```

The live HA test is published by the provisioner and verifies the official
config entry, eleven camera entities, normalized counts, freshness, disabled
controls and Assist exposure. The only entity intentionally exposed to Assist
is `sensor.muse_camera_status`; it contains a bounded summary, not a stream or
camera access token.

The expected healthy state is `normal`. `degraded` identifies one or more
offline cameras while MQTT remains available; `offline` means no camera is
available. `binary_sensor.muse_frigate_data_stale` detects stale or missing
updates. At qualification time, `v5_screen` is correctly reported offline
because its RTSP source at `10.10.50.223:554` times out. Do not hide this signal
or disable the camera to make the test green.

## Rotation and recovery

To rotate, delete the `Frigate Home Assistant Viewer` Keychain item and the
Frigate Home Assistant config entry, then rerun the provisioner. Frigate's
SQLite database is backed up as
`frigate.db.pre-ha-viewer-<UTC timestamp>` before account changes.

To revoke access immediately, remove `homeassistant_muse` in Frigate and delete
the HA config entry. Removing `/config/custom_components/frigate` restores the
pre-integration HA state after a core restart. Never replace the viewer role
with `admin` to repair an unavailable camera; diagnose its RTSP source instead.

Snapshot delivery remains disabled until a specific, authorized Home Assistant
notification target has been selected and tested. Frigate `0.17` also remains
below the integration's `0.18` requirement for native LLM image tools, which
are intentionally not part of this release.

## References

- [Official Home Assistant integration](https://docs.frigate.video/integrations/home-assistant/)
- [Official authentication and port model](https://docs.frigate.video/configuration/authentication/)
- [Official Frigate integration source](https://github.com/blakeblackshear/frigate-hass-integration)
