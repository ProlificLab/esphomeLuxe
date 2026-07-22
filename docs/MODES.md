# Physical modes qualification

`hal.9.0-qualification.1` replaces the old best-effort API exercise with a
transactional test. It binds evidence to the exact ESPHome project version,
refuses an active timer or a non-idle voice pipeline, verifies that voice error,
timeout and recovery counters do not change, and always disables privacy and
continuous conversation before recording the observed cleanup and publishing a
passing JSON record.

## Preconditions

- Finish and archive the uninterrupted `hal.9.0-alpha.2` endurance run first.
- Deploy the reviewed `hal.9.0-alpha.5` OTA to the single canary only.
- Confirm there is no active timer, announcement, music or conversation.
- Keep a person beside the speaker to observe its microphone LED and buttons.
- Choose a new ignored evidence path. Existing evidence is never overwritten
  unless `--overwrite` is explicitly supplied for a discarded test run.

## Transactional API test

Run from the repository root:

```bash
uv run --with aioesphomeapi --with pyyaml \
  scripts/test_hal9_modes.py \
  --expected-version 2025.3.1-hal.9.0-alpha.5 \
  --output release/modes-hal.9.0-alpha.5.json

python3 scripts/check_hal9_modes_evidence.py \
  release/modes-hal.9.0-alpha.5.json \
  --expected-version 2025.3.1-hal.9.0-alpha.5
```

The test performs exactly four ordered transitions: privacy on/off, then
continuous conversation on/off. The active listening phase must report
`voice_health=busy`, matching the firmware state machine; only the final waiting
phase reports `healthy`. A failure still enters the cleanup path and
requires fresh state publications after returning both switches to off, with
`voice_state=waiting` and `voice_health=healthy`. A killed process cannot
guarantee cleanup; in that case,
disable both switches from Home Assistant and verify the visible LED before
retrying with a new evidence filename.

## Manual controls and LED record

The JSON proves API state transitions only. It cannot certify a physical button,
speaker output or visible LED, so record these observations separately:

1. Single press toggles mute without starting a conversation.
2. Long press enters and leaves visible privacy mode.
3. Double press stops active playback and returns to waiting.
4. Triple press enters continuous conversation; the listening LED remains
   unambiguous, and a second press or the bounded timeout closes the session.
5. Day/night brightness changes do not obscure listening, privacy, error or
   rescue colors.
6. A named timer continues its progress color through a day/night transition.

Do not mark the `physical_controls` or stable `hal.9` gates from the API JSON
alone. Attach the reviewed manual record, firmware hash and the validated JSON
to the qualification dossier.

## Failure recovery

If cleanup cannot restore `waiting/healthy`, do not rerun immediately. Capture
the diagnostics, use the documented voice recovery button once, and reinstall
the retained `hal.6` rollback image if the canary does not recover. Never test
another household speaker until the canary record passes cleanly.
