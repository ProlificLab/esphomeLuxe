# hal.9.2-ha-alpha.6 baseline

## Scope

- Secondary authenticated Home Assistant YAML dashboard for local image review.
- Closed camera map for `sonnette` and `avant_jardin` person image entities.
- Explicit review opt-in and destination defaulting to disabled.
- Ten-second arming delay, confidence and camera allowlists, event-ID
  deduplication, 30-second image freshness and five-minute review window.
- Restart closes the window and returns review, destination and camera to safe
  defaults.
- No image copy, public Frigate notification URL, access token, mobile target,
  facial identity or camera/control action.

## Source validation

- Static package and dashboard safety contract: passed.
- Negative fixtures for public snapshot endpoint, external notification,
  one-hour window, third camera, identity processing and default HA restart:
  passed.
- Shell syntax and Python compilation: passed.
- Isolated `homeassistant:2026.7.2` `check_config` with the real package,
  dashboard registration and dashboard YAML: passed; temporary files removed.
- Read-only HA inventory: 44 Frigate image entities, including the two closed
  person images; no mobile app entry, enabled notify entity or device-specific
  notify service.
- Existing HA configuration uses the storage dashboard and has no custom
  `lovelace:` block, so the guarded secondary-dashboard path is applicable.

## Source evidence

- Package SHA-256:
  `3949fab42ffda74adf7195d217676ab2df547af4a643f02803cd23025088f2e0`.
- Dashboard SHA-256:
  `303d12323989870621ae6765fa42437de8e2ba803e272b530e9bfda963055349`.
- Isolated HA fixture SHA-256:
  `351c44ca02ead550772a522bb6f3d02880980a2c59ea30e59f0cb534a9d94adf`.
- Transactional provisioner SHA-256:
  `88d1c659cca882c9cfc0eae9e119ba049430b948e3b9d7021534480889645c8a`.
- Safety checker SHA-256:
  `1f659a71f2da35b3da51d1d4a5698890ee3e2306de888fc24c888a76b571c6a6`.
- Negative fixtures SHA-256:
  `0a57a2b1e936dd4848c09dbcfa3d412ccaaab73b814b2e057ffa22a30630c591`.

## Open gates

- Provision and restart HA only after the uninterrupted firmware endurance run.
- Qualify confidence rejection, exact camera selection, five-minute expiry and
  restart cleanup against a real authorized person event.
- Add a phone only after Companion enrollment and explicit static destination
  review; do not weaken this release with a dynamic notification service.
