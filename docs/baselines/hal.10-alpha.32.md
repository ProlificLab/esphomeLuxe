# Distribution baseline `hal.10-alpha.32`

## Scope

- Prevent an authenticated upload from booting immutable `hal.6` into an
  unverifiable retired credential domain after rotation.
- Preserve USB as the explicit post-rotation immutable recovery path.

## Safety contract

- Artifact SHA-256, immutable manifest MD5/version and credential domain all
  pass before rollback confirmation or upload.
- Active API, OTA and fallback AP values are compared without printing values.
- Active secrets must be current-user private, regular and non-symlink.
- Any rotated key refuses OTA rollback before the destructive boundary.
- No retired credential is escrowed, restored or silently retried.

## Validation

- Four compatibility fixtures cover exact safe domain, each rotated value,
  permissions/symlink and missing/malformed inputs.
- Four exact-install fixtures assert compatibility preflight precedes rollback
  confirmation while artifact and post-boot checks remain mandatory.
- Physical USB recovery remains pending the beta qualification window.

## Source evidence

- Credential-domain checker SHA-256:
  `3e7fcb76de157391573a0739ff5041d3a2d33b51d1ad5d5f374ed90f0be75cec`.
- Compatibility fixtures SHA-256:
  `66f84e9ba259a906a6c1f6520e801504140ba87706da3712ec3bee0a3abca71e`.
- Closed rollback installer SHA-256:
  `3824653c3548b76aca7b246d1848ff4b141bf714319d01b0e74574901b4d8395`.
- Exact-install fixtures SHA-256:
  `cd401738e21681bd4155a7076df4e1a6e32eb11406598c5c0347c6f0ca06e005`.
- Installation guide SHA-256:
  `c26d2572df712a7aa1cefe9a8f70af83bc40de3b2f32d408618ea8b4b839927e`.
- Rotation guide SHA-256:
  `e761d2516b4ae866bccd645c43f6c28029320ff1a1f3c85f38328d1cd967cc95`.
