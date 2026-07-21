# Music Assistant operations

## Validated baseline

- Home Assistant Core `2026.7.2` and Home Assistant OS `18.1`.
- Music Assistant stable app `2.9.9`.
- Server API `192.168.1.59:8095`; published stream endpoint
  `10.10.30.159:8097`.
- Home Assistant source player `media_player.raspiaudio_muse_luxe`.
- Music Assistant entity in HA `media_player.raspiaudio_muse_luxe_2`.
- Home Assistant MediaPlayers is allowlisted to the Muse only.
- Player `announce_volume_strategy` is `none`; the HA package sets and restores
  volume around each announcement.

The local Music Assistant admin account is `chris`. Its generated password is
stored in the macOS Keychain under service `Music Assistant Home`, not in this
repository. To retrieve it intentionally in a private terminal:

```bash
security find-generic-password -a chris -s "Music Assistant Home" -w
```

## Home Assistant integration

Publish and run the idempotent confirmation helper inside Home Assistant Core:

```bash
PVE_HOST=root@proxmox-host \
  scripts/publish_ha_file.sh \
  scripts/confirm_music_assistant_integration.py \
  muse-luxe/confirm_music_assistant_integration.py
ssh root@proxmox-host \
  'qm guest exec 120 -- docker exec homeassistant python \
  /config/www/muse-luxe/confirm_music_assistant_integration.py'
```

The helper confirms only a `hassio` discovery flow at `hassio_confirm`. It
refuses manual authentication flows and returns `already_configured` when run
again.

## Runtime test

After publishing `home-assistant/packages/muse_music_assistant.yaml`, publish
and run `scripts/test_home_assistant_music_assistant.py` inside the Core
container. It verifies the MA player, both guarded scripts, the default-off
transfer opt-in, then plays the local test announcement.

```bash
PVE_HOST=root@proxmox-host \
  scripts/publish_ha_file.sh \
  scripts/test_home_assistant_music_assistant.py \
  muse-luxe/test_home_assistant_music_assistant.py
ssh root@proxmox-host \
  'qm guest exec 120 -- docker exec homeassistant python \
  /config/www/muse-luxe/test_home_assistant_music_assistant.py'
```

A Home Assistant restart temporarily makes the imported player unavailable.
Music Assistant `2.9.9` retried and restored it after approximately 125
seconds in the canary test; the automated test allows 180 seconds. Do not
restart Music Assistant during this window, because that hides the retry path
we need to validate.

## Guardrails and limits

- `script.muse_music_announcement` accepts only URLs below the local
  `/local/muse-luxe/` directory and caps requested volume at 80 percent.
- `script.muse_transfer_audio` is blocked until
  `input_boolean.muse_audio_follow_enabled` is deliberately enabled.
- `input_text.muse_audio_transfer_status` exposes bounded transfer outcomes for
  diagnosis without storing media or credentials.
- Source and destination must be distinct available media players.
- No paid music provider or external account is configured.
- Queue transfer, grouping, position preservation and live intercom still need
  a second satellite and are not release-qualified.
