# Distribution baseline `hal.10-alpha.17`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `interactive_routine_handoff` evidence as a hash-bound path.
- Bind the record to candidate version, OTA, three packages, French sentences
  and the exact HA live test.
- Require two observed players and preserved persisted state across handoff.
- Reject incomplete cleanup, stale-sensor override and critical actions.

## Validation

- Standalone routine evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/source record.
- Tampered and unbound routine records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not physical handoff evidence. Stable remains blocked
until the exact candidate passes with two real satellites.

## Source evidence

- Qualification checker SHA-256:
  `2525767a961324eadd1feb288b3eadad91f22a9697dab10001eb10e446498ee9`.
- Qualification fixtures SHA-256:
  `ea45f54df66e56572b412e04d3f4b0b37310c28f2d2b28044551cfcac3066d63`.
- Qualification template SHA-256:
  `c822aef4fa89d9f7c5669438a60df73e41d665d44098e4e0e11c979a9f715dec`.
