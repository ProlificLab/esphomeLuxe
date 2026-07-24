# Distribution baseline `hal.10-alpha.30`

## Scope

- Collect two independent pinned clean builds into one private source dossier.
- Prove reproducibility, size and log nondisclosure before atomic sealing.

## Safety contract

- Requested release version exactly equals the compiled YAML version.
- Git is clean; private secrets are a non-symlink `0600` file with three real values.
- Output is a newly reserved `0700` directory and is removed on any failure.
- Both builds use the pinned image and explicit clean/compile cycles.
- Unequal OTA hashes, size failure or a private value in any retained log fail.
- Collection has no device host, upload, boot verification or publication step.

## Validation

- Three offline tests cover nondisclosing safe logs, redacted leak findings and
  closed collector ordering through two builds, comparison, budget and sealing.
- Five atomic-sealer tests remain mandatory after collection.
- Real double builds remain deliberately deferred until credential rotation.

## Source evidence

- Closed two-build collector SHA-256:
  `5c44c2a0bd817a18f1df2569935cc27b3e55394bd5ba014788e4d194a24954bf`.
- Private-log disclosure checker SHA-256:
  `4f7b44f035e21f8bc453142802581f9d7ef3388490015c68cde0109c46ae7639`.
- Offline fixtures SHA-256:
  `c82e98ab286307fe07d5f8a2f827af007870511ff2f2d54bda2edbb4e524ee3c`.
- Operator guide SHA-256:
  `bc38f532502494466f05d0f116a7a04184b778cb38a8f32dd4fcfa70f1e4c7fe`.
