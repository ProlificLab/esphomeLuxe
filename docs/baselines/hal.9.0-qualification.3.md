# Source baseline `hal.9.0-qualification.3`

## Scope

- Nine closed phase profiles contain the exact reviewed day/night brightness.
- Six scenarios cover waiting-state API restoration, safety visibility, timer
  transition and HA disconnection.
- Observer and recent timezone-aware observation time are mandatory.
- Candidate version, OTA SHA-256 and HA package SHA-256 are explicit.
- The record complements rather than replaces the guarded waiting-state runtime
  test and physical observation.

## Validation

- Complete profile/scenario fixture: passed.
- Candidate binding, phase set, brightness, pass flag, scenario set/evidence and
  observation-time negative fixtures: rejected.
- No physical LED observation is claimed by this source baseline.

## Open gates

Run only after endurance, paired firmware/HA deployment and the guarded runtime
test. Every example result remains false until observed on the canary.

## Source evidence

- Night LED evidence validator SHA-256:
  `b0ed4752dbd8eb1721c934f1ceb9f29f0c11f206ed01473eaad875d2edeeed2e`.
- Positive and negative fixtures SHA-256:
  `5bb9b9ea6a7084a7cefb6908eff7bca5bda1f26831bd92b47d827a68d7201e7f`.
- Unqualified example record SHA-256:
  `e66855f622c1a6e661bee57c761620274e5640bcac1e48a2901b9a56bbbc1187`.
