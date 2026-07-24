# hal.9.0-alpha.2 baseline

## Scope

- Adds the encrypted native API action `clear_conversation_context`.
- Explicitly clears the ESPHome voice-assistant conversation ID.
- Exposes a diagnostic reset counter for end-to-end verification.
- Contains no additional wake-word model, BLE component or irreversible lock.

## Qualification gates

- Pinned ESPHome compile passed in 288.08 seconds; flash use is 1,869,472
  bytes, or 92.0% of the OTA partition.
- Development OTA SHA-256 is
  `da826ee0ab7ce1279936426dd20bd0269208bacddeed6f4b0212c047480e4f2f`.
- Direct canary OTA passed and the encrypted context-reset action incremented
  its live counter through Home Assistant.
- Privacy, continuous mode, timeout recovery and privacy persistence passed.
- Three reboot cycles returned to `waiting/healthy` in 15.77 to 17.21 seconds,
  with a 16.69-second average.
- A new uninterrupted 24-hour endurance trace is running from the final
  post-qualification boot and remains a promotion gate.

## Rollback

Remove the HA interpreter package before restoring `hal.9.0-alpha.1`, because
the previous firmware does not expose the context-reset API action. The private
`hal.6` artifact remains the final factory-compatible recovery image.
