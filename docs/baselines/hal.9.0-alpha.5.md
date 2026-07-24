# Source baseline `hal.9.0-alpha.5`

## Build

- ESPHome: `2025.10.5`, pinned Docker digest `sha256:def6336...385b0`
- ESP-IDF: `5.4.2`
- OTA size: `1,888,912` bytes, 92.9% of the OTA partition
- Application flash: `1,888,510` bytes, 93.0% as rounded by PlatformIO
- RAM: `40,444` bytes, 12.3%
- OTA MD5: `169ebb5e6811c6416a527719bfa8b422`
- OTA SHA-256:
  `f2067435f7542b522a2834d3747ee12f8cd2aac935bec8029c7834162e02bf5d`

The timer-brightness getter adds 104 application bytes and 112 OTA bytes over
`hal.9.0-alpha.4`. The blocking source budget remains unchanged at less than
93%; no limit was relaxed.

## Scope

- Existing `light.raspiaudio_muse_luxe` entity reused; no new firmware component.
- Firmware timer gradient preserves current brightness across one-second ticks.
- HA brightness-only table covers all nine firmware phases and active timers.
- Every night phase is dimmer than day while listening, privacy, error and
  rescue retain explicit visibility floors.
- Firmware remains sole owner of LED color, effect and safety phase selection.
- HA startup, night-mode, voice-phase and active-timer changes reapply policy.
- Runtime test refuses busy/degraded/timer states and restores the original
  day/night selection in all exit paths.

## Source validation

- Pinned primary firmware compile: passed.
- Main OTA source-size budget: passed at 92.9%.
- Okay Nabu calibration and verbose diagnostic version contracts: passed.
- Isolated Home Assistant `2026.7.2` configuration check: passed without error.
- Night LED static safety contract and eight negative fixtures: passed.
- Five model tests cover every phase, safety visibility floors, timer override,
  non-waiting priority and bounded unknown fallback.
- Existing diagnostics, offline rescue and interpreter contracts: passed after
  the coordinated version bump.

## Source evidence

- HA base package SHA-256:
  `76216f81c392a94d1d52e9a7a56f1039c87b11f70c71ab8bd73379f603943fbb`.
- Firmware recovery package SHA-256:
  `7e2846175601fa4f74990d92370c24acab5a0061f3ab0554cbf714737034a01d`.
- Night LED checker SHA-256:
  `6afd1342ac25b132a3443a4d5a1cc3e9e69105cb7623718f6f80f4b5909ccaca`.
- Negative fixtures SHA-256:
  `f90e565ce63f443e7391d1b2f126c838e13d3708cdc2bfb81b856ef14d3de3ef`.
- Brightness model SHA-256:
  `1fe4d55ae338fda5171d4affaa028f85e4400ffab6f97491c32e48fcccd490ea`.
- Runtime qualification test SHA-256:
  `e0751186ca5ee3d1a1f3602c2d86ec9a066aafa98f48b2d5cf32a99bb5b83792`.
- Transactional paired provisioner SHA-256:
  `26ee379f616c15bfaf41d38457efb622c6dcc11e9b6dfc29cb59f099d441f36d`.

## Open gates

- Do not deploy while the uninterrupted `hal.9.0-alpha.2` endurance run is active.
- After endurance, install firmware and HA package together in one maintenance
  window and run the guarded waiting-state test.
- Physically inspect all phase colors and brightness levels by day and night.
- Start a named timer across a day/night transition and prove every tick keeps
  the selected brightness and progress color.
- Disconnect HA during a timer and prove local progress, completion audio and
  the last brightness remain usable.
- Re-run privacy, continuous-conversation timeout, rescue and rollback gates
  before beta promotion.

`hal.6` remains the production rollback; no update manifest was promoted.
