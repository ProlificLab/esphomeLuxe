# Home Assistant baseline `hal.9.3-ha-alpha.1`

## Acoustic guardian scope

- MQTT listener for Frigate per-camera audio labels.
- Global opt-in defaults to `off`; camera allowlist has no initial value.
- Allowed label defaults to `fire_alarm` only.
- Five-minute default cooldown prevents repeated announcements.
- Warning language says that a compatible sound was detected and requires
  verification; it does not claim a confirmed fire.
- No siren, relay, alarm, camera-control or other critical action is reachable.
- No camera has an Frigate `audio` role, so no real household audio is currently
  analyzed by this feature.

Package SHA-256:
`13f95231ec60c435e39d1cbd22da072bd91a60e2d0ec9d96d94e279a7318e1df`.

## Synthetic validation

- HA configuration check: passed.
- Test topic: `frigate/sonnette/audio/fire_alarm`, payload `ON`.
- Temporary opt-in and camera allowlist accepted the event through real MQTT.
- HA recovered in 8.48 seconds, playback started at 20.38 seconds and returned
  idle at 28.57 seconds.
- Cleanup restart persisted guardian state `off`.
- Last-detection marker: `sonnette:fire_alarm`.
- Temporary startup automation was removed.

## Open gates

- Obtain explicit room/camera consent before adding any real audio role.
- Verify the selected stream contains compatible audio and document recording
  retention before enabling detection.
- Cross-check real fire-alarm detections with dedicated smoke sensors before
  escalating beyond a verification announcement.
- Measure false positives and CPU load per camera with short local retention.
- Design an explicit start/stop and visible session contract before implementing
  continuous interpretation.
- The Muse Luxe microSD bus is not documented in this fork or upstream; do not
  reuse Muse Radio pins. Offline media waits for verified hardware evidence.
