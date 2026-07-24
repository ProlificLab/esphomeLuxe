# Distribution baseline `hal.10-alpha.8`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `night_led_profiles` evidence as a hash-bound relative path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute the HA base-package SHA-256 from candidate source and require an
  exact match in the reviewed record.
- Validate all nine profile values and six physical/runtime scenarios.

## Validation

- Standalone night LED evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/package record.
- Tampered and unbound night LED records: rejected.
- Existing beta, mode, physical-control and endurance bindings remain active.

## Open gates

The source and example are not physical evidence. Stable remains blocked until
the paired candidate passes the guarded API test and all observations.

## Source evidence

- Qualification checker SHA-256:
  `0196ab8c2cb89f58e082c6f58aef66300eea6a0d0f2824ef3f5b62a7aa6d80a3`.
- Qualification fixtures SHA-256:
  `758b2fb735bb73e963d39eee5382f62276cf6bf774bc9d512ac34b98f57c2163`.
- Qualification template SHA-256:
  `07fde5936c09fab5f298eff0e2a7ef2eae80b57ab67e180aaca14972f9494c3a`.
