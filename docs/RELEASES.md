# Release channels

- `development`: automatic clean CI artifact for one canary; never advertised
  by the production updater.
- `beta`: reviewed JSON qualification record, clean rebuild and private family
  test channel.
- `stable`: non-prerelease version, clean rebuild, all physical and endurance
  gates, rollback test and reviewed JSON qualification record.

## Qualification record

Copy `docs/qualification-record.example.json` into the ignored `release/`
directory. Never mark a gate passed until its `evidence` points to a reviewed
CI run, baseline, machine log or physical test record. The checker binds the
record to all of the following:

- exact beta/stable channel and project version;
- full 40-character source commit and a clean worktree;
- SHA-256 of the freshly rebuilt production OTA artifact;
- reviewer, timezone-aware review time no older than 30 days and canary ID;
- exact hardware, Home Assistant, ESPHome and ESP-IDF compatibility matrix;
- qualified feature scope, explicit beta open gates and no stable open gate;
- 13 mandatory beta gates or all 33 stable gates.

Beta includes reproducible build, CI, hard size limit, secrets audit, rollback
artifact, canary OTA, ten reboot/Wi-Fi/HA recovery cycles, privacy reboot,
version-bound API mode transitions, physical controls and 100 TTS cycles.
Stable additionally requires the 93%
size target, 24-hour idle, acoustic calibration, exercised rollback,
second-person install and explicit gates for every `hal.9` family: routed
announcements, timers, night LED, deferred messages, house facts, routine
handoff, authenticated video review and the acoustic guardian, in addition to
intercom, audio transfer, interpreter, camera alerts and offline rescue.

Starting with `hal.9.0-alpha.4`, the 93% target is also a blocking source-CI
gate. Any main OTA larger than 1,889,402 bytes must be optimized or explicitly
reworked; it can no longer pass with a warning.

To obtain the candidate hash before review, run the pinned clean build, then
package locally without publishing:

```bash
docker run --rm -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  clean luxe_microWW.yaml
docker run --rm -v "$PWD":/config -w /config \
  esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0 \
  compile luxe_microWW.yaml
ALLOW_BETA=1 CHANNEL=beta scripts/package_firmware.sh
```

Use `ALLOW_STABLE=1 CHANNEL=stable` only for a non-prerelease stable candidate.
Fill the exact values from `release/build-metadata.json`, attach evidence and
run `scripts/check_qualification_record.py` with the generated manifest and
artifact before requesting review.

Promote only from the same clean commit with:

```bash
PVE_HOST=user@proxmox-host scripts/promote_firmware_channel.sh \
  beta release/qualification-VERSION.json
```

Promotion performs another pinned clean compile and requires the resulting
SHA-256 to match the reviewed record. It uploads a versioned OTA, qualification
record, changelog, dependency diff, build metadata and checksums first. The
channel `manifest.json` is published last and is the only activation point, so
a partial upload cannot redirect the channel to an incomplete release.

The root `manifest_update.json` remains the `hal.6` rollback reference until a
stable promotion is separately reviewed. Firmware binaries contain secrets and
must stay in private HA storage, never a public GitHub release.

## Canary publication

`scripts/deploy_local_update.sh` is an endurance-gated publication step, not an
OTA trigger. It requires a clean worktree, a versioned artifact, its development
manifest, a passing 24-hour summary and the independently reviewed artifact
SHA-256. The preflight recomputes SHA-256 and MD5, validates at least 1,400
samples and every endurance threshold, and requires one identical version.

Only after that preflight does it upload the artifact to
`/local/muse-luxe/channels/development/firmware.ota.bin`, followed by
`manifest.json` in the same private channel. The order is deliberate and the
root `manifest_update.json` rollback pointer is never overwritten.

Publication and installation remain separate operations. Once publication and
the SHA review are complete, `scripts/install_canary_ota.sh` repeats the same
endurance/artifact preflight and requires an exact interactive confirmation.
It passes the reviewed OTA file directly to the pinned ESPHome `espota2`
implementation, then requires the encrypted API to report the expected version,
healthy voice state and no error. It never rebuilds, copies over the root
manifest, or automatically installs a rollback image.

`scripts/rollback_hal6_ota.sh` is the separate recovery path. It accepts only a
retained binary whose SHA-256 is supplied explicitly and whose MD5 and version
match the immutable `hal.6` manifest. A second exact confirmation and post-boot
API check are mandatory. USB recovery remains the fallback when authenticated
OTA is unavailable.

## Changelog and dependency evidence

CI writes two files into every firmware artifact:

- `release/CHANGELOG.md` lists commits and changed files by subsystem;
- `release/dependency-diff.json` inventories the pinned ESPHome image, ESP-IDF,
  minimum ESPHome versions, wake-word models and GitHub Actions, with additions
  and removals since the base release.

Pull requests are compared with their exact base commit. A tag build uses the
previous reachable tag; before the first tag, the report compares with Git's
empty tree. Generate the same evidence locally with:

```bash
python3 scripts/report_release_changes.py --base BASE_TAG --target HEAD
python3 scripts/test_release_report.py
```

Review both files together with the firmware hashes, size report and JSON
qualification record before promoting `beta` or `stable`.
`promote_firmware_channel.sh` regenerates them automatically; set
`RELEASE_BASE_REF` explicitly when the last qualified release is not the most
recent reachable tag.

## Endurance evidence

`scripts/monitor_endurance.py` refuses to append to an existing evidence file
unless `--overwrite` is explicit. In addition to JSONL samples, it writes an
atomic `<output>.summary.json` containing the pass/fail result, thresholds,
memory deltas, error deltas, maximum diagnostic age and uptime regressions.
The summary also records the API host, node, hardware model and exact ESPHome
project version reported by the tested device.
For a stable record, `idle_endurance_24h.evidence` uses the form
`sha256:DIGEST relative-summary.json`. The qualification checker binds the
reviewed digest, loads the safe path relative to the record and verifies 24
hours in monotonic and wall time, at least 1,400 samples, matching firmware
version, fresh diagnostics, memory thresholds, zero reboot, zero voice error
and zero timeout.
The `uptime` heartbeat must remain fresher than 180 seconds by default, so a
silent API disconnect cannot turn frozen values into apparently valid proof.

`mode_api_transitions.evidence` uses the same `sha256:DIGEST relative-path`
form. Promotion loads that exact JSON with
`scripts/check_hal9_modes_evidence.py`, requires the candidate version, four
ordered transitions, unchanged voice counters and a verified safe final state.
This machine gate is additional to, not a replacement for, `physical_controls`.

`physical_controls.evidence` must also be hash-bound. The release checker loads
the exact human observation record with
`scripts/check_physical_controls_evidence.py`, binds it to both candidate
version and OTA SHA-256, and requires all ten button, timeout and microphone LED
observations. Follow `docs/PHYSICAL_CONTROLS.md`; generic gate text is rejected.

For stable, `night_led_profiles.evidence` is another hash-bound record. It must
contain all nine exact day/night brightness pairs and six timer, HA-disconnect
and safety-visibility scenarios. Promotion binds it to the OTA and recomputes
the exact `muse_luxe.yaml` package hash from the candidate source.

`timer_multi_pause_reconnect.evidence` is also mandatory and hash-bound for
stable. It records twelve closed scenarios, two distinct timers, every allowed
checkpoint exactly once at day and night levels, no reconnect replay and one
local completion sound during HA loss. Promotion binds it to the OTA and
recomputes both the base and timer-coach package hashes.

`announcement_routing_queue.evidence` binds the OTA and exact base package. It
requires fifteen closed routing, priority, queue, timeout, volume and failure
scenarios, including restoration after both chime and TTS errors. Targets remain
closed and external deliveries must stay at zero.

`house_intelligence_freshness.evidence` binds the OTA, narrator package,
OPNsense endpoint and ACL, Proxmox audit policy and Frigate read-only policy. It
requires fresh, stale and recovered observations for all four domains, oldest
required-source behavior, deterministic narration, exact read-only roles and
zero infrastructure actions or external deliveries.

`interactive_routine_handoff.evidence` binds the OTA, routine and narration
packages, French intents, live test and fresh-house package. It requires two
distinct available players, preserved session/kind/step across handoff, restart
recovery, all local intents, stale Victron refusal, full reset and zero critical
actions or external deliveries.

`camera_alerts_deduplicated.evidence` binds the OTA, alert/base packages,
safety checker, state model, MQTT provisioning and Frigate read-only policy. It
requires both closed cameras, fresh-event boundaries, seven-ID persistent FIFO,
cross-camera cooldown, night/privacy filters, audible count parity and zero
control action, delivery error or external delivery.

`intercom_two_satellite.evidence` binds the OTA, intercom/base packages, French
sentences, firmware UI/recovery, safety checker, state model and HA lifecycle
test. The common announcement queue revalidates the exact intercom session and
status immediately before TTS. The gate requires 20 calls each way, trusted
physical gestures, session-bound queued relays, timeout/reboot/music checks,
bounded latency and recognition errors, audible/LED parity, zero transcript
artifacts and an entirely empty final state.

`music_transfer_two_satellite.evidence` binds the OTA, Music Assistant package,
safety checker, lifecycle model, HA test and provisioner. It requires music,
radio and podcast transfers in both directions, bounded position drift,
preserved queue/state/relative volume, manual and expiry closure, restart and
failure recovery, and zero automatic transfer, external delivery or ghost group.

The two stable offline gates must reference one identical hash-bound
`offline-rescue` record. It binds the OTA, rescue package, read-only FAT
component and unchanged card manifest, then requires all six clips, fifteen
physical/failure scenarios, one reboot and one HA disconnect/reconnect cycle.

`interpreter_bilingual.evidence` is hash-bound to the OTA, interpreter package,
pipeline configurator and local intent sentences. It pins Granite and both
pipelines, requires five heard phrases in each direction below the latency
limit, all exit/restoration paths and zero Home Assistant actions.

`acoustic_guardian_physical.evidence` binds the OTA, HA package, guarded
preparer, policy template and private candidate hash. It requires consent,
all four classes, two hours per class, bounded false positives and CPU, one-day
retention, disabled transcription and a verified rollback to audio disabled.

`video_review_authenticated.evidence` binds the OTA, package, dashboard and
provisioner. It requires accepted events for both closed cameras, every stale
or unauthorized rejection, two five-minute expirations, HA restart cleanup,
authenticated access and zero public tokens, URLs or external deliveries.

`family_message_delivery.evidence` binds the OTA, queue/base packages and
provisioner. It requires bounded three-slot behavior, FIFO reuse, expiry,
restart quarantine, explicit retry/discard, two recipients, matching carillons,
zero automatic duplicates and a fully empty final/legacy queue.
