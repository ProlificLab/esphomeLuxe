# Distribution baseline `hal.10-alpha.39`

## Trigger

Two local builds of the same alpha.6 source produced different OTA hashes.
Inspection of generated `main.cpp` proved that ESPHome passes compiler
`__DATE__` and `__TIME__` into `App.pre_setup`, so a pinned container alone is
not a reproducible-build guarantee.

## Contract

- `source_date_epoch.sh` resolves a full Git commit and returns only its positive
  commit timestamp.
- CI derives that epoch once and passes it to the main, Nabu and diagnostic
  ESPHome containers.
- Source qualification and beta/stable promotion derive the same value from the
  exact source commit and pass it to both `clean` and `compile` containers.
- Both qualification logs and the sealed source record bind the epoch. Missing,
  malformed or mismatched markers fail closed.
- Release metadata records the epoch alongside source commit, container digest
  and ESP-IDF version.

## Validation

- Before source changes, two real pinned `clean + compile` cycles with production
  secrets and commit epoch `1784732365` both produced OTA SHA-256
  `bea7c06bb6a9648a47ac7cf30e59c42c4d16e0932d7dd35f3772c6d9b056341f`.
- Static and negative fixtures remove epoch derivation, either Docker binding,
  either log marker or metadata field and require rejection.
- No device, Home Assistant, channel publication, credential rotation or OTA is
  touched by this source tranche. The original endurance process continues.

## Source evidence

- Epoch derivation SHA-256:
  `b6812fb9ad55121078158ca1be35b91531a245a65f1cf5b7565626edfadd46d2`.
- CI workflow SHA-256:
  `aa11c5e03160f6a143077c607ca38082fc635c81e088dcf1233f08e14e3a3863`.
- Two-build collector SHA-256:
  `82c8fd343b2e11e42c333f62db645169a3805f66475456dee0d0873ca42240a4`.
- Source sealer SHA-256:
  `2b9072da2789002107de66a64f0a9174df2c43dde8e51258d3a3dbce097d0031`.
- Source validator SHA-256:
  `dc5c388c8926db13e0e9cdbec1e811dcbbcc2e63ce92aaf377ef3b07859adac1`.
- Promotion script SHA-256:
  `e6c02726828e10b3f355625e60955b85095864ff8db976d17948c3e5811d0a2a`.
- Packager SHA-256:
  `60f735604a6402724cb2f1fa88073eb42ea30c29c14b65099660be6b1fbc42a7`.
- Epoch test SHA-256:
  `d88230168ffbc54e037ac0a61af9441e2b30c6d8b5f53ddbd7030570f4c0222a`.
- Source-evidence tests SHA-256:
  `b92e0191d4e3a61079f5b510164e19b3bcf91ce8f0c7202efea6e651a28ccc6f`.
- Source-sealer tests SHA-256:
  `0bddd373dca7b66dc05cc3b5300c1fbb8011b14c1fdc016c92dbe884cc65a7e0`.
- Collector tests SHA-256:
  `51e059bcebda9fbf908483a4a5342466862aa59b500335eed7dbb8dbd5508355`.
- Promotion checker and tests SHA-256:
  `2143ecd2859b258a59512ea6be528be683b8d8cfe9c659ec6d8bc72c309993f8`,
  `17c7cbd5264037b3d71a89ba77e6bdd267a4c476242855c22fd43feb341db9ad`.
