# Source baseline `hal.9.2-qualification.1`

## Scope

- Thirteen closed scenarios cover both cameras, every rejection, matching,
  authenticated access, expiry, restart and absence of external delivery.
- Each mapped camera needs one accepted event and one expired review window.
- Threshold, unmapped-camera, non-person and stale-image rejections are counted.
- One HA restart must restore the closed private state.
- Public URLs/tokens and external deliveries must remain exactly zero.
- Candidate OTA, package, dashboard and provisioner hashes are bound.

## Validation

- Complete video-review fixture: passed.
- Candidate, runtime, final state, scenarios, metrics, boolean and time negative
  fixtures: rejected.
- No camera event or authenticated UI behavior is claimed by this baseline.

## Open gates

Run after endurance using real authorized events from both closed cameras. The
example remains failed until the complete physical/UI protocol is observed.

## Source evidence

- Video-review evidence validator SHA-256:
  `7d242196115e54dc0281da1ee5c2ca9c5ab78bb9c36a21feda66f5f12c048ff0`.
- Positive and negative fixtures SHA-256:
  `8d90d5c83bfde4f2ed12838b20c84797335c3365b45a0451d454ec8abd3ca085`.
- Unqualified example record SHA-256:
  `2d77ea483c504b002d94f800ed754f2b56f3b418c0bb55c8ac9a0432deafd040`.
