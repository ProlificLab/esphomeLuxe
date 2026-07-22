# Physical controls evidence

`hal.9.0-qualification.2` turns the human part of the controls gate into a
closed, candidate-bound record. It complements the encrypted API evidence in
`docs/MODES.md`; neither record can substitute for the other.

## Procedure

1. Finish the active endurance run and deploy the reviewed candidate to the
   single canary.
2. Copy `docs/physical-controls-record.example.json` to an ignored `release/`
   path and fill the exact project version and OTA SHA-256.
3. With one observer beside the canary, exercise volume up/down, single mute,
   long privacy, double stop and triple continuous-conversation start/stop.
4. Let one continuous session reach its firmware timeout without intervening.
5. Confirm the privacy and listening LEDs are visible and unambiguous.
6. Set an observation to `passed: true` only after writing a specific note or
   reference to the reviewed local photo/video/log. Do not reuse one generic
   sentence for unobserved cases.

Validate the record locally:

```bash
python3 scripts/check_physical_controls_evidence.py \
  release/physical-controls-VERSION.json \
  --expected-version VERSION \
  --expected-firmware-sha256 OTA_SHA256
```

Then put its hash and relative filename in the qualification record:

```text
sha256:DIGEST physical-controls-VERSION.json
```

The release checker resolves the path below the qualification directory,
verifies the hash, candidate version and OTA digest, and replays the complete
closed checklist. Records older than 30 days or dated in the future are refused.

## Boundaries

This record covers physical controls and microphone-state visibility only. Day
and night LED levels, timer progress, rescue media, intercom and multi-room audio
have separate stable gates. A human attestation remains human evidence; retain
the referenced local media with the private qualification dossier.
