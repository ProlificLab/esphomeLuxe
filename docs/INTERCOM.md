# Family intercom

## Scope

`home-assistant/packages/muse_intercom.yaml` implements the deterministic
control plane for a family push-to-talk intercom. It does not claim to provide
live or duplex audio. A spoken message is transcribed by the normal local Assist
pipeline and immediately rendered by Piper on the other satellite.

The first source-qualified room map is fixed in the package:

| Room | Player | State |
| --- | --- | --- |
| `bureau` | `media_player.raspiaudio_muse_luxe` | current canary |
| `cuisine` | `media_player.muse_luxe_cuisine` | reserved, not deployed |

An unknown, unavailable or same-room target is rejected before any helper
change or announcement. Update the fixed map only after the second player has
a stable entity ID; never accept an arbitrary entity ID from a voice or model
slot.

## Interaction

- `Appelle la cuisine` requests an audible call from the current `bureau`
  canary. The fixed origin is temporary until each satellite publishes its own
  trusted room identity.
- `Depuis la cuisine appelle le bureau` supplies both rooms explicitly and
  permits the reverse direction without pretending that Assist inferred the
  satellite origin.
- `Accepte l'interphone`, `refuse l'interphone` and `raccroche l'interphone`
  drive the persisted state machine.
- `Interphone depuis la cuisine message ...` relays one transient transcript.
  This explicit room phrase is required until trusted per-satellite origin is
  available.
- An unanswered call expires after 45 seconds. An accepted session expires
  after five minutes and each valid relay restarts that bounded timer.
- A Home Assistant restart changes any `ringing` or `connected` state to
  `error`; it never restores a potentially phantom channel.
- Every accept, decline, hang-up and queued relay carries the current session
  ID. The intercom script and the common announcement queue both recheck the
  session and status at delivery time, so work queued by an old call is rejected
  if a new session starts first.

The central button keeps its local behavior outside an intercom session. During
`ringing`, one click accepts on the called satellite and two clicks decline;
during `connected`, one click starts one normal Assist capture for the explicit
relay phrase and two clicks hang up. Firmware events include one of the two
reviewed device names. Home Assistant verifies that the device belongs to the
current participants and that only the called room can accept or decline.

Every call opening, acceptance, relay and terminal notice uses
`script.muse_announce` with `chime: true`. The Muse firmware displays its normal
playing/answering LED state during each audible signal. There is no continuous
microphone session, so there is no hidden listening interval between relays.

## Privacy and safety

- The intercom is opt-in and defaults to off.
- Only the two fixed room/player mappings are accepted.
- The relay is limited to 240 characters and five queued messages.
- Relay text is not written to helpers, notifications or the logbook. The
  logbook stores source, destination, session ID and state transitions only.
- No raw audio, recording, URL, webhook or direct media action exists in the
  package.
- No duplex mode will be added before two-satellite echo, latency, privacy and
  interruption measurements prove it is preferable to push-to-talk.

Run the source guardrails before publication:

```bash
python3 scripts/check_intercom_safety.py
python3 scripts/test_intercom_safety.py
python3 scripts/test_intercom_model.py
python3 scripts/test_intercom_evidence.py
```

## Home Assistant publication

Publishing is safe during another firmware test because files are inert until
Home Assistant restarts:

```bash
PVE_HOST=root@192.168.1.10 HA_DESTINATION_ROOT=/config/packages \
  scripts/publish_ha_file.sh \
  home-assistant/packages/muse_intercom.yaml muse_intercom.yaml
PVE_HOST=root@192.168.1.10 HA_DESTINATION_ROOT=/config/custom_sentences \
  scripts/publish_ha_file.sh \
  home-assistant/custom_sentences/fr/muse_intercom.yaml \
  fr/muse_intercom.yaml
PVE_HOST=root@192.168.1.10 HA_DESTINATION_ROOT=/config/muse-tests \
  scripts/publish_ha_file.sh \
  scripts/test_home_assistant_intercom.py test_home_assistant_intercom.py
```

Run `ha core check`, then restart Home Assistant only outside another endurance
window. The non-audio lifecycle test must pass before enabling the helper:

```bash
ssh root@192.168.1.10 \
  'qm guest exec 120 -- docker exec homeassistant python \
  /config/muse-tests/test_home_assistant_intercom.py'
```

The test always leaves `input_boolean.muse_intercom_enabled` off. It deliberately
does not exercise a successful call while the cuisine satellite is absent.

## Two-satellite release gate

Do not run this protocol during firmware endurance. Afterward, copy
`docs/intercom-record.example.json` to `release/intercom-VERSION.json` and
perform at least 20 successful calls in each direction. Use only consented test
phrases and never retain their transcript. Verify:

1. The destination carillon and visible audio LED precede every call and relay.
2. Accept, decline and hang-up affect only the current session.
3. Ring and connected timers close the session without a ghost state.
4. A Home Assistant restart and each satellite reboot leave no active channel.
5. Concurrent music is restored cleanly and an urgent announcement preempts the
   intercom.
6. No transcript content appears in helpers, logbook, notifications or backups.
7. End-to-end transcript-to-speech latency and recognition errors are recorded
   in the release baseline.

Exercise stale session IDs, a relay queued before a new call, unknown and
unavailable players, both physical-button devices, 45/300-second timeouts, HA
restart, both satellite reboots, concurrent music and an urgent announcement.
The p95 transcript-to-speech latency must remain at most 15 seconds, the maximum
at most 30 seconds and the recognition error rate at most ten percent. Finish
with intercom disabled, empty helpers, idle timers/players and both voice
satellites `waiting/healthy`.

Validate and bind the resulting record:

```bash
version="REPLACE_WITH_VERSION"
python3 scripts/check_intercom_evidence.py \
  "release/intercom-$version.json" \
  --expected-version "$version" \
  --expected-firmware-sha256 "$(sha256sum "release/muse-luxe-$version.ota.bin" | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_intercom.yaml | cut -d' ' -f1)" \
  --expected-base-package-sha256 "$(sha256sum home-assistant/packages/muse_luxe.yaml | cut -d' ' -f1)" \
  --expected-sentences-sha256 "$(sha256sum home-assistant/custom_sentences/fr/muse_intercom.yaml | cut -d' ' -f1)" \
  --expected-ui-sha256 "$(sha256sum packages/ui.yaml | cut -d' ' -f1)" \
  --expected-recovery-sha256 "$(sha256sum packages/recovery.yaml | cut -d' ' -f1)" \
  --expected-safety-checker-sha256 "$(sha256sum scripts/check_intercom_safety.py | cut -d' ' -f1)" \
  --expected-model-test-sha256 "$(sha256sum scripts/test_intercom_model.py | cut -d' ' -f1)" \
  --expected-ha-test-sha256 "$(sha256sum scripts/test_home_assistant_intercom.py | cut -d' ' -f1)"
```

Set `intercom_two_satellite.evidence` to
`sha256:DIGEST intercom-VERSION.json`. The example remains deliberately failed;
source tests cannot substitute for these observations.

Keep duplex disabled even if these gates pass; it requires a separate measured
echo-cancellation experiment and household consent.
