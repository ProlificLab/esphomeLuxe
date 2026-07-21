# Home Assistant baseline `hal.9.1-ha-alpha.1`

## Scope

This increment runs entirely in Home Assistant and does not change the
`hal.9.0-alpha.1` canary firmware or its production update manifest.

- Chime-prefixed, transcribed push-to-talk messages with no silent listening.
- Immediate delivery when the selected `person` is home.
- One persistent deferred-message slot with recipient, target, text and expiry.
- Explicit refusal to overwrite an occupied slot.
- Automatic once-only delivery on presence, forced manual delivery, expiry
  notification and deterministic cleanup.
- Validation of person and media-player entities before accepting a message.

## Target inventory

- Home Assistant Core: `2026.7.2`
- Person entities: `person.maisonlay`
- Muse media players: `media_player.raspiaudio_muse_luxe`
- Music Assistant: not installed
- Package SHA-256:
  `7ace78f84960cb3a247ecb0431901a2f374d2bd054d8af3036a5fa6696eb0f1a`

The one-slot queue is deliberate for the alpha: it is bounded, survives an HA
restart through input helpers, and cannot lose an older message by accepting a
new one silently.

## Runtime validation

- HA configuration check: passed.
- Deferred message test used the real person and Muse entities.
- HA reconnected after restart in 8.51 seconds.
- The queued or immediate message began playing at 22.61 seconds and returned
  idle at 27.41 seconds.
- The pending flag was persisted as `off` after delivery and the cleanup
  restart.
- The temporary startup automation was removed from the package directory.

## Open gates

- Exercise the expiry branch over its minimum five-minute interval.
- Test presence departure/arrival with distinct family person entities.
- Expand beyond one pending slot only after defining conflict and ordering UX.
- Deploy a second Muse before implementing a live push-to-talk channel.
- Install and configure Music Assistant before implementing queue transfer,
  grouping and position preservation.
- Measure echo and require accept/refuse/hang-up controls before evaluating
  duplex audio.
