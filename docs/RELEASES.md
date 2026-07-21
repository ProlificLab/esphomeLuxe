# Release channels

- `development`: automatic clean CI artifact for one canary; never advertised
  by the production updater.
- `beta`: explicit `ALLOW_BETA=1`, reviewed qualification record and private
  family test channel.
- `stable`: explicit `ALLOW_STABLE=1`, non-prerelease version, all physical and
  endurance gates, rollback test and reviewed qualification record.

Promote only with:

```bash
PVE_HOST=user@proxmox-host scripts/promote_firmware_channel.sh \
  beta docs/baselines/QUALIFIED.md
```

The root `manifest_update.json` remains the `hal.6` rollback reference until a
stable promotion is separately reviewed. Firmware binaries contain secrets and
must stay in private HA storage, never a public GitHub release.
