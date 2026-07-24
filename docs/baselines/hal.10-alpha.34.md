# Distribution baseline `hal.10-alpha.34`

## Scope

- Make a fresh successful 24-hour endurance summary mandatory before real
  credential generation.
- Bind that exact summary to the private rotation bundle and require it again
  at both pre-confirmation and post-confirmation installation boundaries.

## Safety contract

- Endurance evidence must span 24 hours, contain at least 1,400 samples, match
  the candidate version, pass every health threshold and finish within 30 days.
- Evidence over five minutes in the future, stale, short, failed, modified or
  from another version fails before an output directory is created.
- Rotation manifest schema v2 records only the summary SHA-256, version, finish
  time and pass state; no credential or telemetry value is copied into it.
- Summary digest stability is checked around validation to detect concurrent
  modification.
- The installer compares the supplied summary to the bound digest before and
  after operator confirmation, without contacting the canary on failure.

## Validation

- Seven endurance fixtures include exact success, future and expired evidence.
- Six preparation fixtures include short, wrong-version, malformed-version and
  symlink refusal without partial output.
- Six bundle fixtures cover schema, digest, version, permissions and credential
  invariants.
- Four rotated-candidate fixtures retain exact artifact/build/credential binding.
- The complete non-material CI validation block passes locally.

## Source evidence

- Endurance summary checker SHA-256:
  `08ff81f7389897ac62d195a8e9729812b71c29c2eaab9acf7c8aaa548c2cadcd`.
- Offline rotation preparer SHA-256:
  `1f221bcbad4b4c08683449fc490b12f52f133b75e9b6622f183c09aa50ca1e3c`.
- Private bundle checker SHA-256:
  `d4c4907f6ec7df38afd581af9ac8b961bf2f1c84a09474c905aba7525f9f786e`.
- Rotated candidate checker SHA-256:
  `5676b6da03ed7a96e5037dcc8d76760aa1c58cc7993a787c693ca06ddbc0108d`.
- Rotation installer SHA-256:
  `e1f0bc51e1b3a2834d26a275da39532ab9b1489059ceaaed06bcea171c069737`.
- Endurance fixtures SHA-256:
  `358e6b4ffb3f035a6c85fc3cdf0312796f6330ee175062fa8570db73bbbf87a2`.
- Preparation fixtures SHA-256:
  `e694b86d4fd32275e2e5ca57c8eac01eda48839586a2ba5367c31954b8d5dfee`.
- Bundle fixtures SHA-256:
  `dfef51acf3b6cb8ed98adfbac92df56501fd538e0dafbdeda0ac05881351accc`.
- Rotated-candidate fixtures SHA-256:
  `6b6d9eb566bfb6fdcf5c7648eb22cc8e050fad551b70d2d00534dbed3319a87f`.
- Rotation guide SHA-256:
  `2f6873e7c040fac0c3ddf75a40d691519499f23329ab9375f6f54d246bdb7214`.
- Release guide SHA-256:
  `880824767abd150950517e4dbd3afe32732622e3b008bef70a693659779f0cc4`.
