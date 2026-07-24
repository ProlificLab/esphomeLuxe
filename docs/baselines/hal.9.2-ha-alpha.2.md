# hal.9.2 Home Assistant alpha 2 baseline

## Scope

- Six persisted routines: departure, bedtime, server shutdown, power outage,
  alarm and evacuation.
- Explicit start, advance, pause, resume, cancel and reset scripts.
- Local French sentence recognition through Home Assistant's built-in agent.
- Routine target persisted separately so resume can move to another explicit
  media player.
- Human-only steps marked `manual_required`; they cannot advance without an
  explicit confirmation.
- Power-outage evidence checks the MultiPlus connection, valid Victron values
  and the freshest critical telemetry within five minutes.
- Logbook transition records and a normalized read-only routine sensor.
- All critical infrastructure actions absent by design.
- CI allowlist rejects critical infrastructure, arbitrary scripts and
  templated service actions; three unsafe negative fixtures are tested.

## Target evidence

- Home Assistant Core: `2026.7.2`.
- Routine package SHA-256:
  `2ba4af1413c5134d0461d858f9c777da0a8de76ad5725ab658423d43fa495a1e`.
- French sentences SHA-256:
  `d9ea724e83bd81a56019202be95da5f4507788b79710eeb558dbcc0b002fe4e4`.
- Corrected house-intelligence package SHA-256:
  `24c385b36a9c290e2cf31637b3d41769a04d77cc3bc4d3b905d2866f4502c28d`.
- End-to-end test SHA-256:
  `0011851ed48d6f7110bde573c45f10fdc41c99065008de90c39f0f3bc69cbad6`.
- Home Assistant configuration check: passed.
- Real Muse announcement path: passed.
- Disabled guard: passed; routine remained idle.
- Manual confirmation guard: passed; step remained at one.
- Pause, same-speaker resume, cancellation and reset: passed.
- Local French start, pause, resume and cancel intents: passed.
- Real connected/fresh Victron sensor verification: passed.
- Final state: routine `idle`, kind `none`, step `0`, opt-in `off`.

The test found and corrected a false stale-data condition caused by using only
the unchanged 100% battery value timestamp. Freshness now uses the newest of
battery, grid, load and battery-power telemetry together with the physical
MultiPlus connection entity.

## Open gates

- Add and physically validate door/window, lock and occupancy sensors before
  changing departure or bedtime steps from human confirmation to sensor proof.
- Add read-only Proxmox entities before verifying server shutdown state.
- Validate pause on one physical Muse and resume on a second Muse.
- Test alarm and evacuation wording with the family and local safety plan.
- Keep routine opt-in disabled until those phrases and instructions are
  reviewed for the household.
