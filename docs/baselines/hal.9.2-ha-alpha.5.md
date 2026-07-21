# hal.9.2-ha-alpha.5 baseline

## Scope

- Official Frigate Home Assistant integration `5.15.4`, pinned by release,
  commit and SHA-256.
- Dedicated authenticated Frigate `viewer` on port `8971`.
- Eleven camera entities and normalized read-only camera health for Assist.
- All 121 generated control entities disabled and all 449 raw entities hidden
  from Assist.

## Live qualification

- Frigate `0.17.2-3d4dd3a`: healthy container with Coral USB and Intel iGPU.
- Viewer login `200`, profile role `viewer`, statistics `200`, users API `403`.
- Home Assistant `2026.7.2`: integration loaded with 449 entities, 11 cameras
  and 44 images.
- Ten cameras recording; `camera.v5_screen` unavailable due to an upstream RTSP
  timeout at `10.10.50.223:554`.
- Normalized state `degraded`, offline list `[v5_screen]`, source age below 30
  seconds and stale-data sensor off.
- Raw Frigate Assist exposure: zero. Normalized Assist exposure: one sensor.

## Open gates

- Repair or intentionally retire the `v5_screen` source outside this release.
- Select an authorized phone/display before enabling snapshots.
- Restart the uninterrupted 24-hour endurance trace after the final HA restart.
- Revalidate after any Frigate `0.18+` upgrade before considering image tools.
