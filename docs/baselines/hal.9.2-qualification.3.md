# Source baseline `hal.9.2-qualification.3`

## Scope

- Start and resume reject missing or unavailable targets before state mutation.
- Thirty closed scenarios cover six routines, six local intents, manual and
  Victron guards, persistence, cancellation, reset and two-target handoff.
- Two distinct players and two restart recoveries are mandatory.
- Session ID, routine kind and step must survive handoff unchanged.
- Candidate, OTA and all five Home Assistant source hashes are exact.

## Validation

- Static source contract and five unsafe mutations: passed and rejected.
- HA live-test source covers missing/unavailable start and unavailable handoff
  without mutation, with unconditional fixture cleanup.
- Complete routine evidence fixture: passed.
- Candidate binding, targets, runtime, scenarios, metrics, booleans, final state
  and time negative fixtures: rejected.
- No physical two-satellite behavior is claimed by this source baseline.

## Open gates

Run only after endurance and after a second real satellite is enrolled. The
example stays failed until both directions and both restart states are observed.

## Source evidence

- Routine safety checker SHA-256:
  `75cebb92141be73b5d5c4a0418742ead01bba46643cfe80df84b86fcff099939`.
- Safety negative fixtures SHA-256:
  `2552ba2889357d3d748711a0be73eae6926107ff3b0ecb3d54049ca266841405`.
- Expanded Home Assistant live test SHA-256:
  `648c2f4bfe5d1b86b225f85cf4befda92eb239bf9eac5346957af53f35cf0dfb`.
- Routine evidence validator SHA-256:
  `42a00030f38c492065c42d769aed75f1cd53a74fc89450f0a1843ab8b1dbb0a3`.
- Evidence positive and negative fixtures SHA-256:
  `fba01ed99b6ad8b8aea81c30126bdb3aad48a814f42245bd00755a81534d2943`.
- Unqualified example record SHA-256:
  `6f4e85d52c42dc39ac3b6804e5c48318ff6f848daae1c7e56f37135b8e9098ae`.
