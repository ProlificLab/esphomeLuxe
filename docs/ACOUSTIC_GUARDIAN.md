# Local acoustic guardian

The guardian uses Frigate's built-in CPU audio detector on the Chuwi. Frigate
publishes `frigate/<camera>/audio/<label>` and Home Assistant turns an allowed
`ON` event into an advisory announcement. No raw stream reaches the Muse, no
LLM decides the outcome and no siren, lock, relay or camera control is exposed.

## Safety boundary

- The repository policy and Home Assistant helper both default to `off`.
- Home Assistant turns the helper off after every restart to prevent a stale
  opt-in from silently resuming camera listening.
- A ten-second manual arming delay rejects retained MQTT messages received
  during startup or subscription races.
- A camera requires a named room, approver, timezone-aware approval time,
  selected go2rtc input and explicit labels before preparation succeeds.
- The only accepted labels are `fire_alarm`, `glass`, `crying` and `bark`.
- Thresholds are limited to 0.80-0.99 and the RMS gate to 200-2000.
- Event retention is at most one day and automatic transcription is disabled.
- Global audio and transcription settings must remain disabled; only a
  consented camera may override audio locally.
- Audio labels are removed from that camera's alert labels. They remain
  detections and cannot directly cause a critical action.
- The generated file contains the existing private Frigate configuration. It
  stays mode `0600` inside the VM and must never be committed or downloaded.

Frigate retains recordings according to the camera recording policy when an
audio event occurs. The one-day camera detection override also shortens video
detections on the selected camera. Review that tradeoff before enabling it.

## Prepare a candidate

Do this inside the Frigate VM, not in the Git checkout. Copy
`frigate/acoustic-guardian-policy.example.yaml` to a root-only untracked file,
then replace the example entry. Set `enabled` and `approved` to `true` only
after consent. `input_role: detect` is normally the lower-bandwidth go2rtc
restream; verify that this stream actually carries an audio channel first.

```bash
ffprobe -v error -select_streams a \
  -show_entries stream=codec_name,channels,sample_rate \
  -of default=noprint_wrappers=1 rtsp://127.0.0.1:8554/CAMERA

python3 /root/prepare_frigate_acoustic_guardian.py \
  --config /opt/frigate/config/config.yml \
  --policy /root/acoustic-guardian-policy.yaml \
  --camera CAMERA \
  --output /root/config.acoustic-candidate.yml
```

The preparer refuses to overwrite either the active config or an existing
candidate. Inspect its diff locally without printing credentials into a task
log. Validate it with the same Frigate image and private environment:

```bash
docker run --rm --entrypoint python3 \
  --env-file /opt/frigate/config/.env \
  -v /root/config.acoustic-candidate.yml:/config/config.yml:ro \
  ghcr.io/blakeblackshear/frigate:stable \
  -m frigate --validate-config
```

Do not continue if the audio probe or validation fails. Before an eventual
maintenance-window application, make timestamped copies of `config.yml`,
`.env` and the Frigate database, then preserve the candidate as evidence. This
repository deliberately does not provide an automatic apply command.

## Home Assistant

Publish `home-assistant/packages/muse_acoustic_guardian.yaml`, run
`ha core check`, restart Home Assistant and confirm the guardian is `off`.
Set the allowed camera names and labels only after Frigate's physical false
positive and CPU test.

Optional cross-check mappings use comma-separated `label=entity_id` entries:

```text
fire_alarm=binary_sensor.smoke_hall,glass=binary_sensor.window_alarm
```

A corroborating entity adds context to the announcement. Missing, unavailable
or inactive sensors never suppress the warning and never turn it into a
confirmed emergency. Keep the five-minute cooldown until household tests show
that a different value is appropriate.

## Qualification and rollback

1. Enable one consented camera and only `fire_alarm` at threshold 0.90.
2. Measure idle and event CPU, RMS background levels and false positives for at
   least two representative hours before adding another class.
3. Confirm MQTT `ON` and `OFF`, cooldown, the advisory wording and the optional
   cross-check state without activating any physical alarm.
4. Confirm recordings older than one day are deleted for this camera.
5. Turn the HA helper off, restore the dated Frigate config and restart Frigate
   to roll back. Confirm `frigate/<camera>/status/audio` is `disabled`.

For stable qualification, copy
`docs/acoustic-guardian-record.example.json` into the ignored release
directory. Preserve only the SHA-256 of the private Frigate candidate, never
its credentials. Record all thirteen scenarios, at least two representative
hours and one event for each of the four classes, false positives, RMS and CPU.

```bash
python3 scripts/check_acoustic_guardian_evidence.py \
  release/acoustic-VERSION.json \
  --expected-version "VERSION" \
  --expected-firmware-sha256 "$(sha256sum release/muse-luxe-VERSION.ota.bin | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_acoustic_guardian.yaml | cut -d' ' -f1)" \
  --expected-preparer-sha256 "$(sha256sum scripts/prepare_frigate_acoustic_guardian.py | cut -d' ' -f1)" \
  --expected-policy-template-sha256 "$(sha256sum frigate/acoustic-guardian-policy.example.yaml | cut -d' ' -f1)"
```

Stable promotion recomputes all repository hashes and binds the record to the
OTA. It permits at most one false positive per observed hour and a 30-point CPU
increase. The example remains failed until physical qualification is complete.

References: [Frigate audio detectors](https://docs.frigate.video/configuration/audio_detectors/)
and [Frigate MQTT topics](https://docs.frigate.video/integrations/mqtt/).
