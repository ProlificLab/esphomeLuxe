# Distribution baseline `hal.10-alpha.19`

## Scope

- Keep the 13 beta and 33 stable gate names unchanged.
- Require `intercom_two_satellite` as a hash-bound evidence path.
- Bind version, OTA, HA packages, phrases, firmware UI and three test sources.
- Reject altered source, stale observations, fake counts and residual channels.
- Preserve all previously structured stable evidence gates.

## Validation

- Positive stable qualification includes exact intercom source bindings.
- Tampered and unbound intercom records: rejected.
- Forty-one qualification tests: passed.
- The source/example remain explicitly distinct from physical qualification.

## Open gates

Stable remains blocked until two physical satellites complete the exact record.

## Source evidence

- Qualification checker SHA-256:
  `2398a27c5c47cfb4b0f56b2d3ab222d885dcd86ec9bb00c12b32598a666a7023`.
- Qualification fixtures SHA-256:
  `613bdf3302bfeb4a2ee2566caa99f63fc09323d888191e77221884c7fad9bf31`.
- Qualification template SHA-256:
  `744fa1e812bd78fcea7831e1a32008cc34f5463087012efa5b5dd18d91f8793a`.
