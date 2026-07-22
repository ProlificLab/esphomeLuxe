# Distribution baseline `hal.10-alpha.38`

## Trigger

The no-speech correction needs a unique runtime identity before it can replace
the alpha.5 canary. Normal installation correctly rejects the active failed
run, while that correction must be installed before a clean schema-v2 run can
exist. The historical collector in the active process predates summary output,
so its raw trace must be preserved rather than represented as newer evidence.

## Scope

- Identify the corrected production, Nabu and USB diagnostic images as
  `2025.3.1-hal.9.0-alpha.6` variants.
- Seal the exact completed alpha.5 JSONL incident without changing or stopping
  its active process.
- Provide a one-shot corrective installer that cannot qualify or promote a
  release and cannot accept a different transition or fault profile.

## Closed contract

- The incident requires 24 hours, at least 1,400 samples, healthy/waiting at
  start, monotonic counters and uptime, exactly one no-text error, one recovery
  and zero timeout. Any other error text is rejected.
- The sealed record is derived atomically and binds the raw JSONL SHA-256, old
  artifact SHA-256, duration, timestamps, counters and final state. It remains
  explicitly `passed: false` and `purpose: corrective-canary-only`.
- Readiness binds that record to the exact old artifact, exact alpha.6 artifact
  and development manifest, clean source commit and exact successful GitHub CI
  report.
- Installation requires a literal confirmation containing the new version,
  new artifact SHA-256 and incident-record SHA-256. It performs no rebuild,
  publication, rollback or secret rotation.
- Encrypted post-boot verification requires the unique alpha.6 version,
  `waiting/healthy` and no last voice error. A fresh passing schema-v2 24-hour
  endurance remains mandatory afterward.

## Validation

- Offline tests cover the exact accepted incident and reject short duration,
  wrong error/recovery profile, mutated evidence, old artifact, candidate
  version, candidate digest and source commit.
- Static ordering tests require clean-tree check, full readiness, explicit
  confirmation, exact OTA upload and encrypted boot verification in that order.
- No material action, device contact, evidence sealing or OTA upload is part of
  this source tranche. The original endurance process remains untouched.

## Source evidence

- Main configuration SHA-256:
  `9823f5b2ea89abc5103a6932bdda83e0d4576147c8380b410ebb7edc8e99d681`.
- Nabu configuration SHA-256:
  `acb976b638c8ad34ba7e24680039772baa3bc3af8416d3cd36d96e9fa7442246`.
- Diagnostic configuration SHA-256:
  `fe1717774f364edae4a8e617ad395c701df9ae62bc61b8d8a4ff8562bc0d6c79`.
- Incident validator SHA-256:
  `56e9cd8f4986aa6177e82494c077f0c1d245696c275f56d40cc7c70c361ec75a`.
- Incident sealer SHA-256:
  `3514bf6f357e8b6107d441dbcc22fa0c80ed74162c1c5935e2302525459736d0`.
- Corrective readiness SHA-256:
  `948a8b1b1a5a9161222e35b95a090f939d4a2a88bdb77f401beb85ce64173769`.
- Corrective installer SHA-256:
  `fee1910de8b7f6c5311630e8479da2d2f84455c1fcd1a511d090bf9444e82287`.
- Corrective test suite SHA-256:
  `fca53b6669ba27390464b28257a5e779f2d3f2198a45a1fa81b7588d124c7f71`.
- Shared candidate validator SHA-256:
  `6effca01f5b744fa98e4a8d8ed2d07f6811a94ff041bba47d2b135f3a4d136a7`.
- Local OTA artifact: 1,886,720 bytes, 92.8% of the OTA partition. Its exact
  build-instance SHA-256 is reviewed separately at installation and is not
  represented as a stable source hash by this baseline.
