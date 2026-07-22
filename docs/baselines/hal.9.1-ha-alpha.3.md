# hal.9.1-ha-alpha.3 baseline

Status: source qualified and accepted by Home Assistant configuration check;
runtime restart and two-satellite audio qualification open.

## Added

- Deterministic intercom states: `idle`, `ringing`, `connected`, `declined`,
  `timed_out`, `ended` and `error`.
- Fixed `bureau` and reserved `cuisine` room/player mappings.
- Forty-five-second ring timeout and five-minute push-to-talk session timeout.
- Mandatory audible chime for call, acceptance, relay and terminal notices.
- Transient, 240-character transcript relay with no raw audio or text storage.
- French local intents for call, accept, decline, hang-up, relay and status.
- Home Assistant restart guard that refuses to restore an active channel.
- Positive source policy and six negative safety fixtures.

## Source evidence

- `python3 scripts/check_intercom_safety.py`: passed.
- `python3 scripts/test_intercom_safety.py`: passed.
- Python and shell syntax suites: passed.
- Inert Home Assistant publication: package, French sentences and runtime test
  copied with verified SHA-256; `ha core check` passed.
- Runtime non-audio lifecycle test: pending Home Assistant restart outside the
  active firmware endurance window.

## Open hardware gates

- Deploy a second Muse satellite with the exact
  `media_player.muse_luxe_cuisine` identity or update the reviewed fixed map.
- Add a trusted per-satellite origin hook so the short phrase `Appelle la
  cuisine` does not rely on the current fixed `bureau` origin.
- Complete 20 calls in each direction, reboot and timeout cases, music
  interruption, LED/carillon observation and transcript-retention audit.
- Measure transcript-to-speech latency and recognition errors before beta.
- Duplex remains explicitly excluded pending an independent echo study.

No production firmware, update manifest or existing Home Assistant service is
changed by this source-only baseline.
