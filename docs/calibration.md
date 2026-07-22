# Wake-word calibration

The production canary uses `luxe_microWW.yaml` with Okay Hal. The separate
`luxe_microWW_nabu.yaml` build changes only the node identity, wake-word model,
thresholds and version. It must not be published through the production
manifest.

The Nabu build has the same runtime and offline-rescue capabilities as the Hal
build, but no HTTP update entity, so the production Hal manifest cannot replace
it accidentally. Return to Hal with an explicit encrypted OTA upload.

## Profiles

| Profile | Slight | Moderate | Very sensitive |
| --- | ---: | ---: | ---: |
| Okay Hal | 252 | 247 | 230 |
| Okay Nabu | 217 | 176 | 143 |

Record both clean-build footprints in the release baseline before a physical
A/B trial. Nabu should remain slightly smaller because its calibration image
omits HTTP update support; both images must satisfy the same hard flash budget.

The values are model-specific integer probability cutoffs. Never compare their
raw numbers as if they represented equivalent sensitivity.

## Protocol

1. Use the same speaker position, room, firmware toolchain and sensitivity
   label for each model.
2. Play the consented local corpus at fixed near, medium and far positions,
   then record attempts, detections and response latency.
3. Run at least two hours of representative negative household audio and count
   false activations.
4. Repeat once in the day profile and once with night background noise.
5. Store aggregate counts only. Delete raw family recordings after the agreed
   short retention period.
6. Re-run reboot, HA restart, TTS and idle-memory gates before selecting a
   profile.

Use `docs/calibration-results.csv` for machine-readable results. A model is not
promoted solely because it catches more positive samples: false accepts,
latency, memory and recovery stability are co-equal gates.
