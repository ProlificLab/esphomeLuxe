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
- HA configuration check: passed.
- Narrator hardware test: HA recovery 8.32 seconds, playback at 20.36 seconds,
  idle at 38.25 seconds.
- Restored synthesized state after cleanup restart: `normal`.
- Battery: 100%; battery power: 0 W; grid: 568 W; solar: 0 W; load: 549 W.
- Active AC source: `grid`; Victron system state: `external_control`.
- Source age: 44 seconds; stale-data sensor: `off`.
- Automatic energy alerts: confirmed `off`.
- Temporary startup automation removed from the package directory.

## Open gates

- Validate low, critical, stale and recovery transitions with safe synthetic
  fixtures before enabling household alerts.
- Add grid-loss and return announcements only after confirming all Victron enum
  values and testing a controlled outage.
- Define explicitly confirmed, logged and time-bounded load-shedding scripts;
  none are exposed in this alpha.
- Integrate OPNsense and Proxmox as read-only HA entities before narrating their
  status.
- Install Frigate/camera entities before implementing video doorbell alerts,
  confidence thresholds, deduplication or image delivery.
- Add real door, window and occupancy sensors before departure/bedtime routines
  claim to verify household steps.
