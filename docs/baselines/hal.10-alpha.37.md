# Distribution baseline `hal.10-alpha.37`

## Trigger

The active unattended v1 endurance run recorded one exact
`stt-no-text-recognized` event after about 14 hours 23 minutes. The existing
firmware counted it as a voice error and recovery before returning to
`waiting/healthy`. The run is intentionally left intact and will produce failed
evidence because stable policy requires zero errors and zero recovery. It is
never eligible for rotation, canary qualification or promotion.

## Scope

- Separate one exact no-speech STT outcome from infrastructure and voice-pipeline
  failures without erasing observability.
- Upgrade endurance evidence to schema v2 with a bounded no-speech metric and
  an explicit zero-recovery gate.
- Preserve the achieved 93% firmware target.

## Runtime contract

- Only exact code `stt-no-text-recognized` increments `Voice No Speech`; it is
  not a success, error or recovery and returns directly to `waiting`.
- The branch is implemented in one compact trigger lambda. Every other code
  still publishes Last Voice Error, increments Voice Errors, enters the error
  phase for three seconds and invokes normal recovery.
- The no-speech counter is initialized and published through the encrypted API.
  No transcript, message or additional text entity is retained.
- More than three new no-speech sessions in 24 hours fails endurance. This is a
  closed false-wake/no-input ceiling, not a relaxation of error policy.
- Errors, timeouts, recoveries and uptime regressions must each remain exactly
  zero. All monotonic counters also fail if they regress.

## Validation

- Five source-contract suites close the exact code, branch separation, real
  error recovery, diagnostics and both policy limits.
- Seven monitor suites cover healthy operation, stale diagnostics, reboot,
  memory/error/timeout faults, accepted/refused no-speech counts, recovery and
  counter regression.
- Eight summary suites cover 24-hour duration, freshness, reboot, version,
  failed evidence, threshold relaxation, no-speech boundary and recovery.
- Main ESPHome build succeeds with the pinned image at 1,886,720 bytes, 92.8%
  of the OTA partition. Nabu and USB diagnostic configurations are valid.
- No firmware upload or device action is part of this source tranche; the
  original v1 run continues until its evidence is complete.

## Source evidence

- Voice package SHA-256:
  `fff32d1653fd6fa108d94e3c243f6ab733d8a26c70772a536bfeb398711f95c9`.
- Recovery package SHA-256:
  `cd2699bf690a8ea4a52a63e1adf7fbf2b5959be69f1f99339160cc7cc0ce7034`.
- Diagnostics package SHA-256:
  `1a62ca779f324f67383c768adbe6a7d510824d49b889fe3fc76455add3619986`.
- Endurance collector SHA-256:
  `29a4af2cd56394bba24c7b4694d4f6b833b5acb636784f1115d9015404de2a77`.
- Endurance validator SHA-256:
  `55f737a9d05c09c319b0ad080b749449f442835fad96f5ce327668f70d52be9d`.
- Classification checker SHA-256:
  `4dc7a75c4492971c74babb0002ca2c2b1fd70b4f838c78bd657bfa9bcfb6a1e4`.
- Classification fixtures SHA-256:
  `cfbd3429f626f07d53345eb5bfe61d31c219f03492108c62ab69dd79e2590a93`.
- Monitor fixtures SHA-256:
  `a9c4321cd38847dd04e3a11872017100d3b07d5b3ff86648da9a7ddbefa2cc9a`.
- Summary fixtures SHA-256:
  `86364f33e57a1e17096b9e7e963c01d172a836e2818df15c9635956cf1e0be1d`.
- Operations guide SHA-256:
  `2cdd282a6a8c2f09afc61038bfba22156a70a85b7b3ca151f6d3bb4cdc396b43`.
- Release guide SHA-256:
  `d8cc468944bbbc9dca24c3757055a2139481bfc4a6a7cfe46fe5aea976f4ec9a`.
- Canary guide SHA-256:
  `76dc682de74701c62ec18f3661ee032e906f5119c0e7c12ae726ee0e83636459`.
