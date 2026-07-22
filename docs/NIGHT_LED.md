# Day and night LED profiles

`hal.9.0-alpha.5` keeps LED color and effect in the ESPHome phase machine while
`hal.9.0-ha-alpha.3` applies brightness only through the already exposed
`light.raspiaudio_muse_luxe` entity. No new ESPHome component or Home Assistant
sensor is added.

## Profiles

| Phase | Day | Night |
| --- | ---: | ---: |
| Starting | 40% | 15% |
| Waiting | 100% | 10% |
| Playing | 60% | 10% |
| Listening | 100% | 25% |
| Answering | 100% | 20% |
| Offline | 45% | 15% |
| Error | 100% | 35% |
| Privacy | 35% | 20% |
| Rescue | 80% | 35% |
| Active timer while waiting | 40% | 15% |

Night levels are always lower than day levels, but microphone and safety states
retain explicit visibility floors. The HA automation never sets color, effect
or power-off. If HA is unavailable, the firmware keeps the last selected
brightness and continues to own phase colors, privacy indication, rescue and
timer progress.

The timer gradient now reuses the LED's current brightness instead of resetting
it to 40% every second. This prevents API chatter and preserves the selected
profile across countdown ticks. The firmware cost is 104 application bytes and
112 OTA bytes relative to `alpha.4`; the resulting OTA remains below 93%.

## Provisioning

The existing transactional timer provisioner publishes both the base Muse and
timer packages, validates HA and rolls back both files on failure:

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_timer_coach.sh
```

It does not restart by default. Deploy only after the current uninterrupted
firmware endurance run. The firmware and HA package must be promoted together;
the old firmware still resets timer brightness on each tick.

## Qualification

Publish `scripts/test_home_assistant_night_led.py` into HA Core and run it only
in a maintenance window. It refuses degraded, busy, continuous-conversation or
active-timer states. It checks waiting brightness at 100% by day and 10% by
night and restores the original day/night mode in a `finally` path.

Physical qualification must additionally inspect every phase in the table,
start a named timer across a day/night transition, and disconnect HA while the
timer runs. Privacy red, rescue orange and listening green must remain
unambiguous at their night levels.

## Rollback

Restore the timestamped `.pre-timer-coach-*` HA package copies and reinstall the
previous OTA through the documented private rollback path. Do not restore only
one side of the pair. `hal.6` remains the published production rollback until
the complete physical release gate passes.
