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
one exists. Physical room-to-room validation remains required.

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

## Adding sensors

Do not replace a manual step with `sensor_verified` until the physical sensor
has a stable, uniquely named Home Assistant entity and its unavailable,
open/closed and restart behavior has been tested. Keep the entity ID and
expected state fixed in the package; never accept a free-form sensor ID from a
conversation model.
