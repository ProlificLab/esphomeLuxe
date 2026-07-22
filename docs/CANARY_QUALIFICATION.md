# Core canary qualification

This gate is run only after the reviewed 24-hour endurance summary and exact
canary OTA installation. Copy `docs/canary-core-record.example.json` and the
seven raw logs into one ignored, private `release/qualification-VERSION/`
directory. Do not store household credentials, URLs containing tokens or audio
captures in these logs.

## Closed test order

1. Save the successful output of `install_canary_ota.sh` as
   `canary_ota.log`. Record exactly one attempt, the reviewed OTA SHA-256 and
   the encrypted post-boot state.
2. Run `scripts/test_reboots.py` with ten cycles and retain
   `reboot_recovery.log`. Every cycle must return in less than 20 seconds with
   no intervention.
3. Disconnect only the canary client from a dedicated test access point ten
   times, retaining monotonic disconnect/reconnect timestamps in
   `wifi_recovery.log`. Do not power-cycle or block the household AP. Every
   cycle must return in less than 10 seconds with no intervention.
4. Run `scripts/test_ha_restarts.py` with ten cycles and retain
   `ha_restart_recovery.log`. Every `offline -> waiting` recovery must remain
   below 10 seconds.
5. Run `scripts/test_privacy_reboot.py` once and retain
   `privacy_reboot.log`. Privacy must persist across reboot and the cleanup
   block must restore `waiting/healthy` with no error.
6. Run `scripts/test_audio_endurance.py --cycles 100`, count all audible clips
   in the room and retain `tts_cycles.log`. Require 100 requested, completed
   and heard clips, zero failures, voice errors or ring-buffer resets, and a
   healthy final state.
7. Run `scripts/check_rollback_artifact.py` against the separately retained
   private `hal.6` OTA and retain `rollback_artifact.log`. Record its SHA-256,
   immutable manifest MD5, non-zero size and offline storage location without
   putting that private path in Git.

Use `tee` for every command so the reviewed terminal output is the exact file
later bound by SHA-256. A command reporting `SLOW`, a timeout, a manual recovery
or an inaudible TTS fails the entire record; do not average it away.

## Evidence binding

Copy `docs/canary-core-record.example.json` to `draft.json` before the tests.
Fill only the measured `tests` values, the strict `limits`, and
`rollback_artifact.stored_offline`; do not trust manually entered identity,
hashes or pass status. Keep the seven logs under the same evidence directory.

Seal the record only after reviewing every log:

```bash
python3 scripts/seal_canary_core_evidence.py \
  release/qualification-VERSION/draft.json \
  release/qualification-VERSION/canary-core-VERSION.json \
  release/muse-luxe-VERSION.ota.bin \
  release/manifest-development.json \
  release/hal9-endurance-24h-final.summary.json \
  REVIEWED_OTA_SHA256 \
  /private/offline/muse-luxe-hal6.ota.bin REVIEWED_HAL6_SHA256 \
  --logs-dir release/qualification-VERSION/logs \
  --device muse-luxe-canary-bureau \
  --observer "REVIEWER NAME" \
  --started-at "ISO-8601 WITH TIMEZONE" \
  --finished-at "ISO-8601 WITH TIMEZONE"
```

The sealer refuses a dirty worktree or existing output, repeats the reviewed
24-hour/artifact preflight, validates the private rollback artifact, computes
all candidate/rollback/log hashes itself and writes through an `fsync` temporary
file followed by an atomic no-clobber publication in the same directory.
Validation failure or a concurrent output removes the temporary file without
overwriting the winner. Each resulting log binding has this form:

```text
sha256:LOWERCASE_DIGEST relative-log-name.log
```

The sealer validates the final record automatically. It can be checked again
independently before editing the beta qualification record:

```bash
python3 scripts/check_canary_core_evidence.py \
  release/qualification-VERSION/canary-core-VERSION.json \
  --expected-version VERSION \
  --expected-firmware-sha256 OTA_SHA256 \
  --expected-source-commit FULL_COMMIT \
  --expected-device muse-luxe-canary-bureau \
  --expected-rollback-md5 cedf966640caccbabba098bcf22f7645
```

The seven matching beta gates in `qualification-VERSION.json` must all contain
the same hash and relative path for this record. The release checker rejects a
split record, an unbound or escaping path, a modified raw log, a deadline equal
to or above its limit, incomplete counts, stale timestamps, identity drift or
an unsafe final state.
