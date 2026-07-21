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

## Changelog and dependency evidence

CI writes two files into every firmware artifact:

- `release/CHANGELOG.md` lists commits and changed files by subsystem;
- `release/dependency-diff.json` inventories the pinned ESPHome image, ESP-IDF,
  minimum ESPHome versions, wake-word models and GitHub Actions, with additions
  and removals since the base release.

Pull requests are compared with their exact base commit. A tag build uses the
previous reachable tag; before the first tag, the report compares with Git's
empty tree. Generate the same evidence locally with:

```bash
python3 scripts/report_release_changes.py --base BASE_TAG --target HEAD
python3 scripts/test_release_report.py
```

Review both files together with the firmware hashes, size report and physical
qualification record before promoting `beta` or `stable`.
`promote_firmware_channel.sh` regenerates them automatically; set
`RELEASE_BASE_REF` explicitly when the last qualified release is not the most
recent reachable tag.
