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
- Queue transfer, position preservation and live intercom still need a second
  satellite and are not release-qualified.

## Temporary groups

`hal.9.1-ha-alpha.5` adds an explicit temporary-group lifecycle around Home
Assistant's Music Assistant `media_player.join` and `media_player.unjoin`
support. Automatic presence following remains absent and
`input_boolean.muse_audio_follow_enabled` remains off by default.

A request to `script.muse_create_temporary_audio_group` must contain two to
four distinct, currently available entities whose IDs begin with
`media_player.raspiaudio_muse_luxe`. The group lifetime is bounded from five to
240 minutes. Before joining, the script persists the coordinator, members and
claim time; after Music Assistant confirms all members, it restores each
captured volume and starts a restorable timer.

Example after a second Muse has been deployed and validated:

```yaml
action: script.muse_create_temporary_audio_group
data:
  master: media_player.raspiaudio_muse_luxe_2
  members:
    - media_player.raspiaudio_muse_luxe_kitchen
  duration_minutes: 60
```

Close a healthy group with `script.muse_close_temporary_audio_group`. Expiry
calls the same close path. A restart preserves an `active` session only when HA
also restores its active timer. Interrupted `grouping` or `closing`, a missing
timer, an unavailable persisted player, or a two-minute stuck transition moves
the session to `review`; state is not silently cleared.

Recovery is deliberately manual because an automatic unjoin after a partial
failure could stop the wrong playback session:

```yaml
action: script.muse_recover_temporary_audio_group
data:
  confirm_cleanup: true
```

The explicit recovery validates every persisted player again, unjoins all of
them, and clears state only if every action succeeds. Queue transfer is blocked
while any group is active, transitioning or awaiting review.

## Group qualification

1. Enable the manual opt-in and create a two-Muse group for five minutes.
2. Start from different volumes and verify their relative difference after join.
3. Transfer an active music, radio and podcast queue in both directions; verify
   title, queue, elapsed position and play/pause state.
4. Close manually, then repeat with timer expiry and prove no ghost membership.
5. Restart HA with an active restored timer; prove the group remains coherent.
6. Inject failures during join and unjoin, verify `review`, then perform explicit
   recovery without losing the persisted member list.
7. Make one member unavailable before close and prove no successful cleanup is
   claimed until the player returns and recovery is confirmed.

Copy `docs/music-transfer-record.example.json` to
`release/music-transfer-VERSION.json`, complete all 18 scenarios, then validate
it against the exact candidate:

```bash
version="REPLACE_WITH_VERSION"
python3 scripts/check_music_transfer_evidence.py \
  "release/music-transfer-$version.json" \
  --expected-version "$version" \
  --expected-firmware-sha256 "$(sha256sum "release/muse-luxe-$version.ota.bin" | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_music_assistant.yaml | cut -d' ' -f1)" \
  --expected-safety-checker-sha256 "$(sha256sum scripts/check_music_assistant_safety.py | cut -d' ' -f1)" \
  --expected-model-test-sha256 "$(sha256sum scripts/test_music_assistant_group_model.py | cut -d' ' -f1)" \
  --expected-ha-test-sha256 "$(sha256sum scripts/test_home_assistant_music_assistant.py | cut -d' ' -f1)" \
  --expected-provisioner-sha256 "$(sha256sum scripts/provision_music_assistant.sh | cut -d' ' -f1)"
```

Bind the validated record as `sha256:DIGEST music-transfer-VERSION.json` in
`music_transfer_two_satellite.evidence`. Source tests and the failed example do
not constitute physical qualification.
