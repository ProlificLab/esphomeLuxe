# Bounded family message queue

`hal.9.1-ha-alpha.4` replaces the one-message alpha with three persistent
transcript slots. A message is delivered immediately when its selected person
is home. Otherwise the first free slot stores at most 240 characters, recipient,
fixed media-player target, creation ID and expiry for 5 minutes to 24 hours.
An occupied slot is never overwritten and a fourth deferred request is refused.

## Delivery contract

Pending slots are processed in creation-ID order, not numeric slot order. This
preserves FIFO when a low-numbered slot is reused while an older high-numbered
slot remains occupied. Expiry is checked before presence and delivery.

Before TTS, the slot moves from `pending` to `delivering` and records its claim
time. It is cleared only after the audible chime-prefixed message script returns.
If HA restarts during that interval, or a claim remains for six minutes, the
slot moves to `review`. It is never replayed automatically. A person must call
`script.muse_retry_family_message_slot` or
`script.muse_discard_family_message_slot` explicitly.

This is an at-most-once automatic-delivery contract with visible uncertain
quarantine, not an impossible exactly-once claim across a TTS or HA crash. An
explicit retry may repeat audio that actually played before the crash; review
the recipient and transcript first.

No raw recording, URL, token or external notification target is stored. The
existing `script.muse_intercom_message` validates the fixed media-player target
and always emits the audible carillon before Piper renders the transcript.

## Legacy migration

The deprecated one-slot input helpers remain temporarily so a pending alpha.1
message is not lost during upgrade. Two seconds after the first restart:

- an unexpired, complete message is submitted to the new queue;
- an already expired message produces a local expiration notice and is not
  extended or delivered;
- legacy helpers are cleared only after migration succeeds.

Keep these legacy helpers until the physical migration gate passes. They no
longer own a dispatcher or queue script.

## Provisioning

The transactional provisioner backs up both package files, publishes them,
runs `ha core check` and restores both on any publication or validation error:

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_family_messages.sh
```

It does not restart HA by default. Use `RESTART_HA=1` only after the current
firmware endurance run and after inspecting
`input_boolean.muse_pending_message`. If the legacy flag is on, verify its
recipient, target and expiry before restart without displaying its transcript
in a shared terminal.

After restart, publish and run the non-audio lifecycle test inside HA Core. It
uses only an empty slot, changes it to `review`, discards it and verifies all
fields are empty; it refuses to touch any `delivering` slot.

```bash
PVE_HOST=root@192.168.1.10 HA_DESTINATION_ROOT=/config/muse-tests \
  scripts/publish_ha_file.sh \
  scripts/test_home_assistant_family_messages.py \
  test_home_assistant_family_messages.py
```

Then execute `/config/muse-tests/test_home_assistant_family_messages.py` in the
Home Assistant Core container through the Proxmox guest agent.

## Physical qualification

1. Queue three different consented transcripts while recipients are away and
   prove a fourth is refused without changing the first three.
2. Free slot 1, add a newer message, then prove the older slot 2 is delivered
   first when the recipient returns.
3. Exercise the minimum five-minute expiration without audio.
4. Restart HA with a synthetic slot in `delivering`; prove it becomes `review`
   and remains silent until explicit retry or discard.
5. Verify an immediate message consumes no queue slot.
6. Verify every delivered message has a carillon, bounded text and the selected
   recipient/room; test two distinct person entities when available.
7. Confirm all states and transcripts survive a normal restart and cleared
   fields remain empty after delivery.

For stable qualification, copy `docs/family-message-record.example.json` into
the ignored release directory. Record all sixteen scenarios, two recipients,
automatic/immediate/manual outcomes, quarantine, expiration and carillons, then
leave every current and legacy slot empty. Validate the exact candidate:

```bash
python3 scripts/check_family_message_evidence.py \
  release/family-message-VERSION.json \
  --expected-version "VERSION" \
  --expected-firmware-sha256 "$(sha256sum release/muse-luxe-VERSION.ota.bin | cut -d' ' -f1)" \
  --expected-package-sha256 "$(sha256sum home-assistant/packages/muse_family_messages.yaml | cut -d' ' -f1)" \
  --expected-base-package-sha256 "$(sha256sum home-assistant/packages/muse_luxe.yaml | cut -d' ' -f1)" \
  --expected-provisioner-sha256 "$(sha256sum scripts/provision_family_messages.sh | cut -d' ' -f1)"
```

Stable promotion recalculates all source hashes and binds the record to the
OTA. The example remains failed and contains no family transcript.

## Rollback

Turn message automations off by stopping HA, restore both timestamped
`.pre-family-messages-*` package backups, validate and restart. If any new slot
is non-empty, record only its ID, recipient and state for manual handling before
rollback; do not silently discard or replay its transcript.
