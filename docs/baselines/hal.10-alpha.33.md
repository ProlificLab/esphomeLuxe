# Distribution baseline `hal.10-alpha.33`

## Scope

- Bind both reproducible builds to the exact private credentials file mounted
  read-only in the pinned ESPHome container.
- Refuse rotated canary installation unless artifact, source evidence and new
  credential bundle form one reviewed identity.

## Safety contract

- Source evidence schema v2 records one private-file SHA-256 without values.
- Both build logs contain that exact fingerprint and the exact OTA SHA-256.
- The private file remains current-user owned at mode `0600` and its digest is
  checked before and after each build.
- Rotation revalidates the complete source record, OTA size/hash, bundle and
  credentials fingerprint before confirmation or any device write.
- Wrong artifact, version, bundle, old schema, modified log or symlink fails
  closed without contacting the canary.

## Validation

- Eight source-evidence fixtures cover identity, CI, size, secrets audit and
  credential-binding drift.
- Six atomic-sealer fixtures require private mode and both build bindings.
- Four rotated-candidate fixtures cover exact success and all cross-identity
  failures without disclosing credential values.
- The complete non-material CI validation block passes locally.

## Source evidence

- Source evidence checker SHA-256:
  `cd8b17d5a6876b67cd1565e9ce9c584a2c86279fe266355676723aa9770dfaaf`.
- Atomic source sealer SHA-256:
  `93e0fd3d3235df0fddae89b8b095f820e9dcadef06cbb2ac8097e0ad395ccf94`.
- Two-build collector SHA-256:
  `d8aff88d33f74b27648bcdfb030469d24053d7020407cac6f42f73b27314b4f6`.
- Rotation binding checker SHA-256:
  `97948b8e41697fa3a8145e03a06ab8a8ae1bfd848943a66136ab154308e20c65`.
- Rotation installer SHA-256:
  `6f43c27feba8e5a9cee063e8b1e1f87d99337c4f1668f701b5e019fa25fcf5be`.
- Rotation-binding fixtures SHA-256:
  `7f04d12b662fb326129c3cff1514de518460c952e3d8ab62dcde699a4c02f0a3`.
- Source-evidence fixtures SHA-256:
  `77afc1f22c17b1ee1218479d460de757c847e7308099ec32b13c9fc9aac63409`.
- Source qualification guide SHA-256:
  `e96f97dca70f018c30370480e3700c0a329b594cecbe2326647d674cee793175`.
- Secret rotation guide SHA-256:
  `0a32937b7402ac66f18e62f4e38bc355704ec9348ffead4703fd1a8d5ab64ca6`.
- Source record example SHA-256:
  `ef82b7e029844296bcc2e825c4d863a22efb0cc8130dbe3ad4b58831c7f9a93b`.
