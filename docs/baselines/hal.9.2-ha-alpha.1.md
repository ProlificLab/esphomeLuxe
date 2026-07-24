# Home Assistant baseline `hal.9.2-ha-alpha.1`

## Scope

- Read-only normalized energy status built from current Victron sensors.
- Source timestamp and age included with every factual snapshot.
- Explicit stale-data state after three minutes or unavailable battery data.
- Deterministic French narration with no LLM-generated facts.
- Opt-in low/critical battery alerts with two-minute confirmation and urgent,
  bounded announcement delivery.
- Recovery announcement only after five minutes back in the normal state.

The package never targets a Victron `number`, `select`, `switch` or `button`.
Automatic alerts default to `off` and therefore cannot surprise the household
before threshold review.

## Target evidence

- Home Assistant Core: `2026.7.2`
- Package SHA-256:
  `5556562702c9a298701274879860a951091a974977e462d23db8928257bb7ff5`
- Video-alert package SHA-256:
  `048fbe59374183a49b27a1121c315f22e3490f33ebb21f06fb43b494c701ba74`
- Frigate MQTT provisioning script SHA-256:
  `03488e1480c08f35859e894cf1be80a0f941f5e974ce9527195b4f720adf1374`
- HA configuration check: passed.
- Narrator hardware test: HA recovery 8.32 seconds, playback at 20.36 seconds,
  idle at 38.25 seconds.
- Restored synthesized state after cleanup restart: `normal`.
- Battery: 100%; battery power: 0 W; grid: 568 W; solar: 0 W; load: 549 W.
- Active AC source: `grid`; Victron system state: `external_control`.
- Source age: 44 seconds; stale-data sensor: `off`.
- Automatic energy alerts: confirmed `off`.
- Temporary startup automation removed from the package directory.

## Frigate event path

- Frigate VM 110: 11 configured cameras and healthy container after restart.
- Dedicated random Mosquitto login stored outside Git; MQTT availability `on`.
- Frigate files backed up with suffix
  `.pre-mqtt-20260721T192516Z` before provisioning.
- Video announcements default to `off` and were returned to `off` after test.
- Synthetic `person` event on allowed camera `sonnette`, confidence 0.99:
  passed through the real broker and HA automation.
- HA recovered in 8.08 seconds, playback started at 20.15 seconds and returned
  idle at 24.71 seconds.
- Filtering includes allowed cameras, person-only label, false-positive flag,
  confidence, event-ID deduplication, cooldown and night-mode suppression.
- No facial identity, camera control, alarm control or public image URL exists.

## Open gates

- Validate low, critical, stale and recovery transitions with safe synthetic
  fixtures before enabling household alerts.
- Add grid-loss and return announcements only after confirming all Victron enum
  values and testing a controlled outage.
- Define explicitly confirmed, logged and time-bounded load-shedding scripts;
  none are exposed in this alpha.
- Integrate OPNsense and Proxmox as read-only HA entities before narrating their
  status.
- Install the optional official Frigate HA integration before adding camera
  entities, authenticated snapshots or phone image delivery.
- Add real door, window and occupancy sensors before departure/bedtime routines
  claim to verify household steps.
