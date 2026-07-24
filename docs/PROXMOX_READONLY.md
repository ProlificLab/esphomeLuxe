# Proxmox read-only integration

`hal.9.2-ha-alpha.3` gives the house narrator real Proxmox facts without giving
Home Assistant, Assist or the conversation model infrastructure controls. The
setup follows the
[official Home Assistant Proxmox VE guidance](https://www.home-assistant.io/integrations/proxmoxve/)
to use a dedicated user and API token with the minimum `PVEAuditor` role. Token
creation and privilege separation follow the
[Proxmox `pveum` reference](https://pve.proxmox.com/pve-docs/pveum.1.html).

## Security model

- Proxmox user: `homeassistant@pve`; no PAM or root password is used.
- Revocable token: `homeassistant@pve!homeassistant`, privilege separation on.
- Both user group and token ACL are propagated at `/` with `PVEAuditor` only.
- Effective permissions are parsed as JSON and every granted privilege must end
  in `.Audit`; `Sys.Audit` and `VM.Audit` are mandatory.
- The token secret is streamed over SSH stdin into a temporary `0600` file in
  HA Core, consumed by the config flow and deleted in a `finally` block.
- A local backup of the token secret is stored in macOS Keychain service
  `Proxmox Home Assistant API`, never in Git or shell output.
- The integration creates control buttons even for an auditor. The hardener
  disables all of them with `disabled_by=user` and rejects any Proxmox entity
  exposed to Assist.

## Provisioning

Publish both in-HA helpers, then run the idempotent provisioner:

```bash
PVE_HOST=root@proxmox HA_DESTINATION_ROOT=/config/muse-tests \
  scripts/publish_ha_file.sh scripts/configure_proxmox_readonly.py \
  configure_proxmox_readonly.py

PVE_HOST=root@proxmox HA_DESTINATION_ROOT=/config/muse-tests \
  scripts/publish_ha_file.sh scripts/harden_proxmox_readonly.py \
  harden_proxmox_readonly.py

PVE_HOST=root@proxmox scripts/provision_proxmox_readonly.sh
```

The provisioner is safe to rerun. If a token exists but HA has no matching
integration, it stops rather than replacing an unrecoverable secret. Set
`ROTATE_TOKEN=1` only for an explicit revocation and replacement.

## Narrator and test

Publish `home-assistant/packages/muse_house_intelligence.yaml`, run
`ha core check`, restart HA and publish the test into `/config/muse-tests`.
Validate live entities without audio, or add `--announce` for the physical Muse
path:

```bash
python3 /config/muse-tests/test_home_assistant_proxmox.py
python3 /config/muse-tests/test_home_assistant_proxmox.py --announce
```

The normalized `sensor.muse_proxmox_status` reports node, HAOS, Frigate,
LibreNMS and Ollama states, node CPU/memory/disk and last backup. HAOS and
Frigate are critical; the intentionally stopped Ollama container is reported
but does not mark the platform degraded. A five-minute telemetry guard prevents
the narrator from presenting stale server facts as current.

## Revocation

If the credential is suspected to be exposed, revoke it immediately on
Proxmox, remove the HA integration entry, delete the Keychain item, then rerun
the provisioner with explicit rotation:

```bash
pveum user token delete homeassistant@pve homeassistant
security delete-generic-password -a 'homeassistant@pve!homeassistant' \
  -s 'Proxmox Home Assistant API'
ROTATE_TOKEN=1 PVE_HOST=root@proxmox \
  scripts/provision_proxmox_readonly.sh
```

Do not grant `PVEVMUser`, `PVEVMAdmin`, `VM.PowerMgmt`, snapshot or permission
management privileges to this integration.
