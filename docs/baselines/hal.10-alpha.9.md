# Distribution baseline `hal.10-alpha.9`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `timer_multi_pause_reconnect` evidence as a hash-bound path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute the base and timer-coach package hashes from candidate source.
- Validate all twelve scenarios and exact timer metrics.

## Validation

- Standalone timer evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/package record.
- Tampered and unbound timer records: rejected.
- Existing beta, mode, controls, LED and endurance bindings remain active.

## Open gates

The source and example are not physical evidence. Stable remains blocked until
the paired candidate passes every timer observation after endurance.

## Source evidence

- Qualification checker SHA-256:
  `e6b62ae43f93fdc50d60e83febd5e9dbb7b16799d254eb65f87e60229c86f4a7`.
- Qualification fixtures SHA-256:
  `1dfa78c2da40b76de9f1e5342973984ef9a1ae7e4d63f9e859cfefab19e66289`.
- Qualification template SHA-256:
  `4a642b48a96b3b4d2577a86d805448c04e623ec9184164b02f001baab837ddda`.
