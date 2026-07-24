# Home Assistant baseline `hal.9.1-ha-alpha.2`

## Scope

- Music Assistant stable app `2.9.9` installed and onboarded locally.
- Supervisor-discovered HA integration confirmed without storing HA
  credentials.
- Home Assistant MediaPlayers provider allowlisted to the Muse only.
- Guarded local announcement with explicit volume restoration.
- Manual queue transfer, disabled by default and rejecting identical or
  unavailable source/destination players.
- Reproducible integration confirmation and end-to-end runtime tests.
- Package SHA-256:
  `cf44231b0ae0cdfc8436bcb57bdf026887dff0911b8ee23fa9e0e1319478c1f7`.

## Runtime validation

- Music Assistant server and stream endpoints reachable on ports `8095` and
  `8097`.
- Muse registered available with play, volume, mute and announcement support.
- Direct Music Assistant announcement passed and restored state to `idle`.
- HA configuration check passed after package publication.
- HA Music Assistant announcement passed through
  `script.muse_music_announcement` and returned to `idle`.
- Transfer opt-in remained `off`; a real request ended as
  `blocked_disabled`.
- After an HA restart, the MA Home Assistant provider recovered in about 125
  seconds; the test timeout is 180 seconds.
- The unsupported native announcement-volume warning was removed by setting
  `announce_volume_strategy=none` and managing volume in HA.

## Open gates

- Deploy a second Muse and repeat transfer in both directions with active
  music, radio and podcast queues.
- Verify position preservation, relative volume and temporary grouping.
- Implement audible accept/refuse/hang-up controls before live intercom audio.
- Keep the one-slot transcribed-message path as the only validated intercom
  behavior until those physical tests pass.
