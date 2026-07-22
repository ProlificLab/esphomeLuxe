# Source baseline `hal.9.0-qualification.2`

## Scope

- Ten closed physical observations cover volume, mute, privacy, stop,
  continuous-conversation start/stop/timeout and microphone-state LEDs.
- Every observation requires a passing boolean and non-placeholder evidence.
- Observer, room and timezone-aware observation time are mandatory.
- Records older than 30 days or more than five minutes in the future fail.
- Candidate device, hardware, project version and lowercase OTA SHA-256 are
  explicit and independently checked.
- The record does not absorb separate night LED, timer, rescue or multi-room
  gates.

## Validation

- Complete positive fixture: passed.
- Wrong version/hash, missing/unknown observation, false/placeholder result,
  stale/future time and malformed digest fixtures: rejected.
- No physical test has been claimed by this source baseline.

## Open gates

Copy the example only after endurance and canary deployment. A household
observer must perform every case and retain the referenced private evidence.

## Source evidence

- Physical evidence validator SHA-256:
  `1324c23459c2062f73a2f806d3cc6d78eebec735f3c46a93c85ac8033942e49f`.
- Positive and negative fixtures SHA-256:
  `246c1e541741b85e6443c65387c6a4cb9d510990f6284ee76842cd8f7a521551`.
- Unqualified example record SHA-256:
  `023c23245b89f19339f5c30f9a3a82fa41c0029bffa5f31f0bd1fcefbf1c998d`.
