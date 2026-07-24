# Distribution baseline `hal.10-alpha.41`

## Trigger

The corrective path validated its inputs before asking for explicit human
confirmation, leaving a time-of-check/time-of-use window before the mounted
host artifact reached ESPHome's uploader. Normal canary and rollback paths had
the same byte-identity gap.

## Contract

- Normal and corrective canary installers repeat their complete candidate
  preflight after confirmation.
- The rollback path repeats both immutable `hal.6` artifact validation and
  credential-domain compatibility after confirmation.
- Every OTA entry point supplies the reviewed SHA-256 to the pinned uploader.
- The uploader rejects invalid digests, empty files and symlinks, copies the
  candidate to a private container-local snapshot, fsyncs it and verifies its
  SHA-256 before invoking `espota2` on that independent copy.
- A host mutation after confirmation cannot alter the bytes read by `espota2`.

## Validation

- Offline tests prove the snapshot survives mutation of its source file.
- Negative tests reject wrong or malformed hashes, empty files and symlinks.
- Installer source tests require post-confirmation revalidation and exact hash
  forwarding on normal, corrective and rollback paths.
- Shell syntax, the full source workflow and all firmware variants are checked
  without contacting the canary during its active endurance.

## Source evidence

- Exact uploader SHA-256:
  `e316208e0270aa67fff6fcc86bd370df95c82b2a3dc6ed97d556273e0e21323f`.
- Uploader fixtures SHA-256:
  `571362cf0340a28c389ed5ecf41c8229c35c045e0b0ad5313adbebf4443b83a9`.
- Normal installer SHA-256:
  `244e6dfa5f22070adf29ff0191a62fde3bb434b65450473ded59e8099cc8747b`.
- Corrective installer SHA-256:
  `4fd182205414874b76fca23f61b00042887b91ffba57c525bd42939d5420aaca`.
- Rollback installer SHA-256:
  `49efa396dbb7b33ce7ffe669665a37fd79c07aee923d73b9284cdc5f7486a4a2`.
- Installation guide SHA-256:
  `3cd3cb05f4a022fea2ba1c3b9828dd644cc8341be88da455d3a8c3ad1fbaf91e`.
- Release guide SHA-256:
  `49d87f8d5d98ac55fd5e92f30afc629d7081b946b9b641799c1e44d87bc9a172`.
