# Distribution baseline `hal.10-alpha.21`

## Scope

- Refuse canary publication before a clean, successful 24-hour endurance gate.
- Bind the reviewed SHA-256, manifest MD5, artifact filename and project version.
- Permit only the private development URL and publish its manifest last.
- Preserve the root `hal.6` rollback manifest and never trigger OTA directly.

## Validation

- Five readiness tests cover the exact candidate and all identity failures.
- Short endurance, wrong version, digest, project, channel, path and name: rejected.
- Shell syntax, ordering, complete policy suite and existing firmware budget: passed.
- No file was published and no OTA or restart was triggered.

## Source evidence

- Readiness checker SHA-256:
  `0969344504f6b3f36a928f7b2f5831d9756c81bbeaf8dee6b9cede93d18a0daa`.
- Readiness fixtures SHA-256:
  `6ba71ce846fd92efddca7026c3ab93bdb6be7fdfed255816cc1263413727337b`.
- Canary publisher SHA-256:
  `5eec2d076550f8789e4e1346e9d41bc218021d48d8fc936ab7ba41b719c16328`.

## Open gate

Run this command only after the active monitor writes and validates its final
summary. Physical OTA qualification remains a separate observed operation.
