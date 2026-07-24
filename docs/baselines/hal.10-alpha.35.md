# Distribution baseline `hal.10-alpha.35`

## Scope

- Close the post-rotation USB recovery boundary around the exact retained
  `2025.3.1-hal.6` OTA application.
- Remove the public example credential file from the authenticated rollback
  trust path.

## Safety contract

- The immutable OTA SHA-256 remains
  `8a8350fa93293ef8421f4c84004c4804a2969ae6d50697a72e104ba85d4db0d6`
  and its MD5/version must still match `manifest_update.json`.
- A USB factory image must have an independently supplied reviewed SHA-256,
  start as an ESP32 image, contain the exact OTA at `0x10000`, and end exactly
  with that application. Symlinks, altered prefixes, wrong offsets and trailing
  bytes fail closed.
- The checker emits only public digests, sizes, version and offset. It never
  reads, reconstructs or prints credentials.
- Authenticated `hal.6` rollback now requires an explicit current-user-private
  `0600` `HAL6_REFERENCE_SECRETS` file. Example credentials always fail before
  confirmation or device contact.
- A historical source rebuild using ESPHome `2025.10.5` was deliberately not
  retained as recovery evidence: its OTA used example credentials, was 16 bytes
  shorter and did not match the archived OTA SHA-256.

## Validation

- Seven USB fixtures cover exact embedding, both immutable digests, wrong
  offset, trailing data, modified application, symlink input and manifest
  mismatch.
- Five credential fixtures cover an exact private domain, each rotation,
  permissions, symlinks, public examples and malformed input.
- Four installer structure fixtures prove the rollback reference is explicit
  and the public example file cannot re-enter the command path.
- The real rebuilt factory/archived OTA pair is expected to fail the new gate.
- No device operation is part of this source-only tranche; the 24-hour
  endurance run remains uninterrupted.

## Source evidence

- USB recovery checker SHA-256:
  `df278f3cf517807afc5e4e68aec2c477f7c769c57abaa29f1e671857e27d9119`.
- USB recovery fixtures SHA-256:
  `c7350b9e2df40e1b656f55b2c3bbfca8c9f2f51a2bd427e77098d9297e628153`.
- Credential-domain checker SHA-256:
  `a4eccc1716aed85bb26e2f801c686996f5da570266787e9cfb5fafc19b6761e8`.
- Credential-domain fixtures SHA-256:
  `0fbb02e02e94bcfde3787383dcc53cf04de59c0d7e57ef37da5b34e44f8546e8`.
- Authenticated rollback command SHA-256:
  `a1cc93ed87183a649a5c09b1ff451153d109fca8d840ab198a8496bcf0a1e949`.
- Installer structure fixtures SHA-256:
  `0e72abfc483cbbf0924a41c68d176386b0ecccc23c8c6f1c957eaac81235f233`.
- Installation guide SHA-256:
  `b4ba33052da86a9f66e1061e36b906abe0ea7f2f5a941d7d675390b70544967e`.
- Secret-rotation guide SHA-256:
  `4b50f658fc75e7debd519e26a89e09877cbcdb644800e9bbf825ad486d776e9a`.
- Release guide SHA-256:
  `21c2afb093025257257087294e3f83451f961607cede177c2f45cb7565fc5352`.
