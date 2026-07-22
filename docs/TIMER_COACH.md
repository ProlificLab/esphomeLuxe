# Timer checkpoint coach

`hal.9.0-ha-alpha.2` adds optional spoken checkpoints to the native Assist
timers already held by the Muse Luxe. The ESP32 remains the timer owner after
creation: it tracks multiple named timers, updates the remaining-time LED and
plays the embedded completion sound without Home Assistant.

## Checkpoint contract

`input_boolean.muse_timer_checkpoint_announcements` is off by default. When it
is explicitly enabled, Home Assistant observes the nearest active timer and
queues normal-priority announcements at five minutes, one minute, 30 seconds
and 10 seconds remaining.

A checkpoint is accepted only when a normal countdown crosses it by at most
five seconds. Initial state, unavailable state, reconnect jumps, duration
changes and timer switches are not replayed. This deliberately prefers a
missed intermediate notice over a duplicate or stale notice. The embedded
completion sound is independent of this package.

Checkpoint speech uses `script.muse_announce`, so it inherits day/night volume,
the bounded ten-minute queue and volume restoration. Non-urgent announcements
now also wait while the Muse is starting, listening, answering or in continuous
conversation. Urgent announcements retain their explicit interruption path.

The firmware receives pause, resume and duration changes through ESPHome's
native timer update event. A paused timer is retained by the native timer list,
but the current LED and HA diagnostics intentionally represent only active
countdown time. Physical pause/resume feedback remains a qualification gate.

## Provisioning

The provisioner backs up the base and timer packages, publishes both, validates
Home Assistant and rolls both back if publication or validation fails:

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_timer_coach.sh
```

It does not restart Home Assistant by default. After the firmware endurance run
and during a maintenance window, use `RESTART_HA=1`. The feature remains off
after restart and must be enabled explicitly.

## Physical qualification

1. Create two named timers through Assist and verify count, nearest name and LED.
2. Pause and resume each timer, then change one duration and cancel the other.
3. Enable checkpoint announcements and verify each allowed checkpoint occurs
   once at day volume and once at night volume.
4. Play music and open a continuous conversation across checkpoints; prove the
   normal notices wait and drain in order after audio and conversation stop.
5. Disconnect Home Assistant after timer creation. Confirm local countdown and
   completion audio, reconnect, and prove no missed checkpoint is replayed.
6. Trigger an urgent test announcement during a timer checkpoint and verify the
   urgent path interrupts cleanly without losing timer completion.

## Rollback

Leave the opt-in switch off, stop Home Assistant, restore the timestamped
`.pre-timer-coach-*` copies of both package files, validate and restart. No timer
or message payload is stored by this package.
