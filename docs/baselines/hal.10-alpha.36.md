# Distribution baseline `hal.10-alpha.36`

## Scope

- Produce a canonical, credential-preserving `hal.6` USB recovery image from
  reviewed components without reconstructing or exposing retired secrets.
- Bind its historical source, flash layout and artifact identities in a tracked
  machine-readable provenance record.
- Provide a closed physical USB flash command without touching the active
  endurance canary.

## Canonical identity

- Historical firmware commit:
  `6f5b3a93320380a50a910376491d1c7381ba1fc8`.
- Historical CI-only commit:
  `63c89e723f4175a2fc79fda922dcfd8eef5f2f7b`.
- ESPHome image digest:
  `sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0`.
- Reviewed 64 KiB prefix SHA-256:
  `845bf05b4e85a991d0f79f397172d10e538c1d903f76623bc1a17e74c4733656`.
- Exact OTA SHA-256:
  `8a8350fa93293ef8421f4c84004c4804a2969ae6d50697a72e104ba85d4db0d6`.
- Canonical 2,013,680-byte factory SHA-256:
  `16ad19ae504dae9e75d6be0cb72b6ada34bf932fae0f972a89b5230dc20c01ac`.

## Safety contract

- Composition accepts only regular non-symlink inputs, the exact OTA and the
  exact reviewed prefix. It requires the bootloader at `0x1000`, partition
  marker at `0x8000` and donor application at `0x10000`.
- Output is `0600`, synchronized, linked into place without overwrite and never
  partial. The immutable OTA begins at `0x10000` and is the final byte range.
- The public provenance record closes both commits, the container digest, four
  offsets, sizes, MD5 and SHA-256 values. CI cross-checks it against Git,
  `manifest_update.json`, `luxe_partitions.csv`, the workflow and both tools.
- The USB flasher accepts only an explicit local non-symlink character device,
  repeats both gates around literal confirmation and pins `esptool==5.3.1`.
  It never uses force, full erase, network OTA, secrets files or readback copies.
- The canonical private image was composed and independently validated locally
  in `artifacts/recovery/` with mode `0600`. It was not flashed to hardware
  during the still-running 24-hour endurance test.

## Validation

- Six composition fixtures cover canonical private output, atomic no-overwrite,
  altered prefix, altered OTA, symlink and short donor.
- Eight image fixtures cover exact identity and layout, both hashes, offset,
  trailing data, embedded mutation, partition marker, symlink and manifest MD5.
- Four provenance suites cover the tracked record, identity mutations,
  strict schema and symlink refusal while proving both historical commits.
- Four flash structure fixtures enforce validation order, serial-device scope,
  pinned esptool and absence of unsafe flags or secret material.
- A real non-device invocation refuses before validation or serial access.

## Source evidence

- Composer SHA-256:
  `250cc09f8ab296dd1761e77b50ca4bf2dee719b041f1798e7804bf1deabe704e`.
- Factory checker SHA-256:
  `07b3c319965ead0f66df28ce5bce3d126bb6fc37d01554cb85e3a3070117e127`.
- Provenance checker SHA-256:
  `e514cceb5a4d8c2f1818395ad7f4889623a007b1eeb7961c8f898afe4708dbc1`.
- USB flasher SHA-256:
  `fed99418c794460c0260719edee3d2f617fc8fbd1ee86e6ef112b4bb0c3a771e`.
- Composition fixtures SHA-256:
  `e6cd4f719cc70d9d017874fb473fcf9f93e67d30cfe2f09c6478fc6a3cc134c5`.
- Factory fixtures SHA-256:
  `4ac39228a81862694667b39ff726d9089dc589f797063f7f4a81405724c90240`.
- Provenance fixtures SHA-256:
  `19105d02918656c9503cfbdea3202294cf16dd23f4ea926c8eb10473bfce82d8`.
- USB flash fixtures SHA-256:
  `b68d52a8287e64fed853cce9f2a451df8ba5f8e9c84acf544819b24ff59520ac`.
- Provenance manifest SHA-256:
  `ceca3dfa047e89527b0db646f46b66161475f4cc60e7967b2aa2f40969ccf02e`.
- Installation guide SHA-256:
  `a25774a8922f9d9628af5b5069810a8dd4b99cfee494f6ca4f158058b8bdc60d`.
- Rotation guide SHA-256:
  `9ecb5b3c3e1ee014e0bad266fe549b067ce2b2d0e9b790b98612a514cab59124`.
- Release guide SHA-256:
  `563aaebfb2929a048fae9ef04c1c4f01d605abd5b8f7d74ad689f904457ba148`.
- Updated `hal.6` baseline SHA-256:
  `3b4d4f5fb7b4533bf089b36327d5102cbf30a030ae81c928aba60a5fdcae83ae`.
