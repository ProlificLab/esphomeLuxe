# Distribution baseline `hal.10-alpha.6`

## Scope

This source-only increment closes release-matrix omissions. It does not mark a
feature qualified, deploy firmware or restart Home Assistant.

- Keep the 13 beta gates unchanged.
- Expand stable qualification from 25 to 33 explicit gates.
- Add routed announcement queue, multi-timer pause/reconnect, night LED,
  deferred family delivery, fresh house facts, routine handoff, authenticated
  video review and physical acoustic guardian gates.
- Keep wake-word acoustic calibration separate from the acoustic guardian.
- Keep API mode evidence separate from physical controls.
- Require the checked-in qualification template to exactly equal the executable
  stable gate set.

## Validation

- Positive beta and 33-gate stable fixtures: passed.
- Template/executable equality and beta/stable separation: passed.
- Missing timer gate fixture: rejected.
- Existing false, missing, hash, commit, prerelease, open-gate, endurance and
  mode-evidence negative fixtures remain rejected.

## Open gates

Every new template entry remains `passed: false` with placeholder evidence.
Each must be exercised on the canary and independently reviewed before stable
promotion; this baseline proves coverage of the release checklist, not physical
feature behavior.

## Source evidence

- Qualification checker SHA-256:
  `91c93826508276e248c33cdfe2082af899ea359c4a7d1b09d7832997e9cbe6d7`.
- Qualification fixtures SHA-256:
  `df64da65523c10e4994369c9870eb717ea70931c467f7b2beb05fdef3fdd852f`.
- Qualification template SHA-256:
  `cd3fb35ed64624682bebb2497c6b6ae38a0782cc573cdcb38db4b49d5cdbe206`.
