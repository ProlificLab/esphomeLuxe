# Distribution baseline `hal.10-alpha.31`

## Scope

- Compile the exact selected rotated secret set in both qualification builds.
- Reject a saved CI run that is not the current clean source commit before build.

## Safety contract

- One non-symlink `0600` secret file is resolved once after its real-value audit.
- Its absolute path is read-only over-mounted at `/config/secrets.yaml` in both
  pinned Docker clean/compile cycles, overriding any stale repository fixture.
- CI JSON has the exact schema, canonical URL, positive integer IDs, current
  full commit and exactly one completed successful `compile` job.
- CI or credential identity failure occurs before the first expensive build.
- No device, upload or activation action is added.

## Validation

- Four CI-preflight fixtures cover exact success, commit/run/URL/status drift,
  duplicate/missing/failing jobs, booleans, schema and malformed JSON.
- Three collector fixtures require both explicit read-only secret mounts and
  preflight ordering before the two-build comparison.
- Real private builds remain deferred until endurance review.

## Source evidence

- Corrected source collector SHA-256:
  `9d2a4e9e267d225c02da183a825fb335df1d9b3646f529de7801ce78c40043b3`.
- Collector fixtures SHA-256:
  `542cdc24503db19b78f3451799cea698b3d77e585e0b09f4737b3a4f792dc6b1`.
- Exact CI preflight SHA-256:
  `3fc18ae753aad1fb5875415c766eaefb91e6f8820af13dc2566c171860ddc5b1`.
- CI-preflight fixtures SHA-256:
  `0858ac281f4ac9b48a61cb1d9b5d16b3353612e8bc09d53e6ff6b0af82925885`.
- Operator guide SHA-256:
  `5a54ed194950c28f11c4b44b2b21859249a02f6f788a1e98e6c0ab988d9f9d3e`.
