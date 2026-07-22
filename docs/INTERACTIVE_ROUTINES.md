# Interactive routines

`hal.9.2-ha-alpha.2` adds deterministic, persisted checklists for departure,
bedtime, server shutdown, power outage, alarm and evacuation. The routines are
disabled by default with `input_boolean.muse_routines_enabled`.

## Safety model

- A routine guides and records; it never shuts down Proxmox, controls an alarm,
  unlocks a door or sheds an electrical load.
- Every transition is recorded in the Home Assistant logbook and in persisted
  helpers exposed by `sensor.muse_interactive_routine`.
- Steps without a real sensor remain `manual_required` until a person gives the
  explicit confirmation phrase. The UI never labels them sensor-verified.
- The first power-outage step is the only current `sensor_verified` step. It
  requires the MultiPlus connection entity, valid Victron values and a critical
  telemetry update less than five minutes old. Voice confirmation cannot
  override a stale-data block.
- Alarm and evacuation are urgent spoken checklists, not alarm-system controls.

## Local French commands

These phrases are handled by Home Assistant's local conversation agent, before
any LLM fallback:

- `Commence la routine départ` (also `coucher`, `arrêt serveur`, `panne`,
  `alarme` or `évacuation`)
- `Confirme l'étape de la routine`
- `Mets la routine en pause`
- `Reprends la routine`
- `Annule la routine`
- `Où en est la routine`

The service `script.muse_resume_routine` accepts another explicit
`media_player` target, so a paused routine can move to a second satellite once
one exists. Start and resume now reject both missing and `unavailable` targets
before changing persisted state. Physical room-to-room validation remains
required.

## Installation and test

```bash
PVE_HOST=root@proxmox HA_DESTINATION_ROOT=/config/packages \
  scripts/publish_ha_file.sh \
  home-assistant/packages/muse_interactive_routines.yaml \
  muse_interactive_routines.yaml

PVE_HOST=root@proxmox HA_DESTINATION_ROOT=/config/custom_sentences \
  scripts/publish_ha_file.sh \
  home-assistant/custom_sentences/fr/muse_routines.yaml \
  fr/muse_routines.yaml

PVE_HOST=root@proxmox HA_DESTINATION_ROOT=/config/muse-tests \
  scripts/publish_ha_file.sh \
  scripts/test_home_assistant_routines.py \
  test_home_assistant_routines.py
```

Run `ha core check`, restart Home Assistant, then execute inside HA Core:

```bash
python3 /config/muse-tests/test_home_assistant_routines.py
```

The test deliberately produces several announcements. It validates disabled
and manual-confirmation guards, pause/resume/cancel/reset, the local French
intent path and the real Victron freshness check. It always cleans up the
routine and returns the opt-in helper to `off`, including after a failure.

CI also runs `scripts/check_routine_safety.sh`. It requires the opt-in,
verification and logbook markers and accepts only an explicit action allowlist;
critical infrastructure, arbitrary scripts and templated service actions are
rejected.

## Stable qualification

Copy `docs/routine-record.example.json` into `release/` only after two distinct
satellites are available. Exercise all six routine kinds and all six local
intents. Pause on the first satellite, resume explicitly on the second, and
verify that kind, step and session ID are unchanged before hearing that same
step from the second target. Repeat once in the other direction. An unavailable
handoff target must leave both the old target and paused state unchanged.

Restart Home Assistant once while `running` and once while `paused`; persisted
state must survive. Verify manual confirmation, fresh Victron sensor proof and
the stale Victron block that voice cannot override. Alarm and evacuation must
use urgent audio; the other routines stay normal. No routine may call an
infrastructure control or deliver data externally.

Finish by cancelling or completing, resetting, disabling the opt-in and
checking both players `idle`, voice `waiting/healthy`, status `idle`, kind and
verification `none`, step zero, and all identity text helpers empty.

```sh
version="REPLACE_WITH_VERSION"
python3 scripts/check_routine_evidence.py \
  "release/routine-$version.json" \
  --expected-version "$version" \
  --expected-firmware-sha256 "$(sha256sum "release/muse-luxe-$version.ota.bin" | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_interactive_routines.yaml | cut -d' ' -f1)" \
  --expected-sentences-sha256 "$(sha256sum home-assistant/custom_sentences/fr/muse_routines.yaml | cut -d' ' -f1)" \
  --expected-live-test-sha256 "$(sha256sum scripts/test_home_assistant_routines.py | cut -d' ' -f1)" \
  --expected-house-package-sha256 "$(sha256sum home-assistant/packages/muse_house_intelligence.yaml | cut -d' ' -f1)" \
  --expected-base-package-sha256 "$(sha256sum home-assistant/packages/muse_luxe.yaml | cut -d' ' -f1)"
```

Bind the validated record in `interactive_routine_handoff.evidence` as
`sha256:DIGEST routine-VERSION.json`. Neither this guide nor the failed example
is physical evidence.

## Adding sensors

Do not replace a manual step with `sensor_verified` until the physical sensor
has a stable, uniquely named Home Assistant entity and its unavailable,
open/closed and restart behavior has been tested. Keep the entity ID and
expected state fixed in the package; never accept a free-form sensor ID from a
conversation model.
