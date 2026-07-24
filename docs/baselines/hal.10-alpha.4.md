# Distribution baseline `hal.10-alpha.4`

## Scope

This source-only increment hardens idle-endurance evidence. It does not change,
publish or deploy the canary firmware and does not restart Home Assistant.

- Track the age of the periodic ESPHome `uptime` heartbeat.
- Stop and fail when diagnostics remain stale beyond 180 seconds by default.
- Reject any uptime regression as an unexpected device reboot.
- Refuse to reuse an existing JSONL path unless `--overwrite` is explicit.
- Write a machine-readable summary atomically beside the JSONL evidence.
- Bind that summary to the API host, node, model and reported project version.
- Require stable qualification to bind the evidence SHA-256, then load and
  validate that exact file.
- Preserve the existing heap, PSRAM, voice health, error and timeout gates.

## Validation

- Five monitor tests cover a healthy run, stale telemetry, reboot, memory/error
  regressions and atomic JSON summary output.
- Six evidence tests cover duration, freshness, reboot, firmware binding,
  failed-run rejection and relaxed-threshold rejection; qualification tests
  reject missing or modified evidence.
- The existing 24-hour `hal.9.0-alpha.2` process is intentionally unchanged;
  this monitor revision applies to the next complete qualification run.

## Open gates

- Complete the already-running alpha 2 endurance gate with its original monitor.
- Run a new full 24-hour qualification with this freshness-aware monitor on the
  eventual release candidate.
- Keep all physical and two-satellite gates open until exercised on hardware.
