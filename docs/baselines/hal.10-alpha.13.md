# Distribution baseline `hal.10-alpha.13`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `video_review_authenticated` evidence as a hash-bound path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute package, dashboard and provisioner hashes from source.
- Enforce closed cameras, rejection coverage, expiry, authentication and cleanup.

## Validation

- Standalone video-review evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound video-review records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not physical/authenticated evidence. Stable remains
blocked until the exact candidate completes both real-camera review windows.

## Source evidence

- Qualification checker SHA-256:
  `745ff4aa6b38dac6de342459e572b3836eaea8d237711d40419ee98dd4159911`.
- Qualification fixtures SHA-256:
  `7f13d580c520fdab7118313deb14cdcf967947dafddeee8bfd11bf356e271a35`.
- Qualification template SHA-256:
  `5d7d234ffe2b2b0da6020da6d1befb56ef92890a4d3087613f67d9a9cd645e11`.
