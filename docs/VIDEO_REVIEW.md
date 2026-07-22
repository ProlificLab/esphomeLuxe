# Authenticated Frigate image review

`hal.9.2-ha-alpha.6` offers a local image review without creating a public
Frigate notification URL or granting camera control. A qualifying MQTT person
event selects one of two closed Home Assistant image entities for five minutes:

- `sonnette` -> `image.sonnette_person`
- `avant_jardin` -> `image.avant_jardin_person`

The secondary `Revue video Muse` dashboard is served by Home Assistant and uses
its normal authenticated frontend. The package stores only the bounded event
ID, selected camera and timestamps. It never copies image bytes, embeds an
access token, identifies a person or sends data to a phone or external service.

## Limits

The Frigate integration image entity represents the latest person image for a
camera, not an immutable event-specific snapshot. The automation accepts it
only when its update timestamp is within five seconds before the event start
and no more than 30 seconds old. The dashboard still asks the viewer to verify
that the image corresponds to the displayed event ID.

Closing the five-minute review window hides both conditional image cards. It
does not delete or alter Frigate recordings, snapshots or their configured
retention. Those remain governed by the existing authenticated viewer setup.

There is currently no Home Assistant Companion mobile app or enabled `notify`
entity on this installation. The source therefore does not pretend to deliver
to a phone. A future mobile destination needs a separately reviewed static
service mapping and physical delivery test; dynamic notification targets are
not accepted.

## Provisioning

The provisioner publishes the package and dashboard, adds a secondary YAML
dashboard while preserving the primary storage dashboard, backs up
`configuration.yaml` and runs `ha core check`:

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_video_review_dashboard.sh
```

It refuses to merge into an existing unknown `lovelace:` block. Previous
package, dashboard and configuration files receive timestamped backups; all
changed files are restored if publication or validation fails. It does not
restart Home Assistant by default. Use `RESTART_HA=1` only in a maintenance
window after the firmware endurance run is complete.

After restart, confirm the review helper and destination are respectively
`off` and `disabled`. Deliberately select `ha_dashboard`, enable review, wait
ten seconds, then publish a synthetic non-person event first to prove it is
ignored. Test a real person event only on an authorized camera.

## Qualification

1. Confirm an event below the configured confidence threshold is rejected.
2. Confirm cameras outside the closed map and configured allowlist are rejected.
3. Confirm a fresh allowed event opens the correct conditional card.
4. Compare the displayed event ID and camera with Frigate before trusting the
   latest image.
5. Confirm the card and persistent notice disappear after five minutes.
6. Restart HA with an open window and confirm review returns to `off`,
   destination to `disabled` and camera to `none`.
7. Confirm no `/api/frigate/notifications/` URL, image token or mobile message
   appears in helpers, logs or notifications.

For stable qualification, copy `docs/video-review-record.example.json` into the
ignored release directory. Test both mapped cameras and every rejection path,
let both five-minute windows expire, perform one HA restart and leave the
review state closed. Validate the exact candidate and sources:

```bash
python3 scripts/check_video_review_evidence.py \
  release/video-review-VERSION.json \
  --expected-version "VERSION" \
  --expected-firmware-sha256 "$(sha256sum release/muse-luxe-VERSION.ota.bin | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_video_review.yaml | cut -d' ' -f1)" \
  --expected-dashboard-sha256 "$(sha256sum home-assistant/dashboards/muse-video-review.yaml | cut -d' ' -f1)" \
  --expected-provisioner-sha256 "$(sha256sum scripts/provision_video_review_dashboard.sh | cut -d' ' -f1)"
```

Stable promotion recalculates every source hash and binds the record to the
OTA. The example remains failed and is never a substitute for the authenticated
physical review.

## Rollback

Turn review off, restore the timestamped
`configuration.yaml.pre-muse-video-review-*` backup, remove
`/config/packages/muse_video_review.yaml` and
`/config/dashboards/muse-video-review.yaml`, then validate and restart HA.
Frigate itself does not need a restart because this feature never changes it.

Reference: [official Frigate Home Assistant image entities](https://docs.frigate.video/integrations/home-assistant/).
