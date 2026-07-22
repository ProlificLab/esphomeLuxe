# Source baseline `hal.9.0-qualification.6`

## Scope

- The queued announcement path is limited to 25 calls and a ten-minute normal
  busy wait.
- Day, night and urgent volumes are exact; urgent playback may preempt audio.
- Previous volume restoration continues after chime and TTS failures.
- Fifteen closed scenarios cover routing, FIFO, priority, waits, timeout,
  carillon ordering, error injection and final cleanup.
- Candidate version, OTA and exact Home Assistant package hashes are required.

## Validation

- Static source contract and seven unsafe mutations: passed and rejected.
- Complete announcement evidence fixture: passed.
- Candidate binding, runtime, scenarios, metrics, booleans and time negative
  fixtures: rejected.
- No physical announcement behavior is claimed by this source baseline.

## Open gates

Run the protocol only after endurance. The unqualified example remains failed
until all observations have been performed on the canary.

## Source evidence

- Announcement safety checker SHA-256:
  `9ede0345f08edc3262afe82f4d07bafdff11bf22e0741ff84cf7f990f354b296`.
- Safety negative fixtures SHA-256:
  `e3bb35c0c273aeafb243f489eb070575064ef6f7c5e5ce55bad91a1cb0c51691`.
- Announcement evidence validator SHA-256:
  `0e8777e5efe9972ad6fbd9280e926399f0a70e10f19dda3972c0841d57f462a3`.
- Evidence positive and negative fixtures SHA-256:
  `ed2a366b67af60b6eff27a53beb4d98a1ca63d6449a6d3b4dea700cbca10cf1d`.
- Unqualified example record SHA-256:
  `d3a1725ef74c1b08d645a80d0692f1373673e3fa21f0efc55e569f92dac7ef55`.
