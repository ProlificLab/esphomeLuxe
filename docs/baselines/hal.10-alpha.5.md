# Distribution baseline `hal.10-alpha.5`

## Scope

This source-only increment binds the transactional mode qualification to every
beta and stable promotion. It does not deploy or restart any device.

- Add `mode_api_transitions` as the thirteenth beta and twenty-fifth stable
  gate while retaining the independent `physical_controls` gate.
- Require `sha256:DIGEST relative-path` evidence under the qualification record
  directory and reject absolute paths, traversal, missing files or hash drift.
- Load the exact evidence and validate candidate version, ordered transitions,
  unchanged counters and safe cleanup.
- Keep the existing stable endurance binding on the same shared safe-path
  resolver without weakening any endurance policy.

## Validation

- Beta and stable positive qualification fixtures: passed.
- Existing missing gate, false gate, commit/hash mismatch, prerelease stable,
  stable open gate and endurance binding fixtures: rejected.
- Tampered and unbound mode evidence fixtures: rejected.
- The standalone mode evidence and source-safety suites: passed.

## Open gates

- Generate real mode evidence only after the active endurance run and canary OTA.
- Complete the separate physical button, LED and audio observations.
- Keep beta and stable promotion blocked until every other mandatory gate has
  independently reviewed evidence.

## Source evidence

- Qualification checker SHA-256:
  `93dd70ab695c70964c692ac55aefcbd4565876c0029f3ca5d15b9f68f0167c69`.
- Qualification fixtures SHA-256:
  `e89c1c81e1088e4184a4664d9bb77f7622a6089682a40525b739c2de04f1823e`.
- Qualification template SHA-256:
  `884d0f8ac563211c4ddfceea923e7059141c478ffc967e82d0b3410d7b271215`.
