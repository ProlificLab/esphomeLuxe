# OPNsense read-only telemetry

The house narrator reads current gateway facts without receiving any firewall,
routing or failover control. Home Assistant's native OPNsense integration is a
device tracker, so this project installs a deliberately smaller companion API:

```text
GET /api/muse/status/gateways
```

The endpoint returns only sanitized results from OPNsense's existing
`interface gateways status` backend action. Its ACL contains one exact path,
the controller rejects non-GET requests, and the `homeassistant_muse` account
has only `page-muse-readonly`. This avoids the standard `System: Gateways`
privilege, which also covers mutable routing APIs.

OPNsense uses an API key and secret through HTTP basic authentication. The
secret exists only in Home Assistant's ignored `secrets.yaml` and the local
macOS Keychain. The repository contains neither credential. TLS verification
is disabled only because the current LAN endpoint uses its self-signed
certificate; replacing it with a trusted local certificate is a later hardening
step.

Home Assistant polls `192.168.1.1`, the management interface already allowed
from that VM. The API remains blocked on the services VLAN address
`10.10.30.1`; provisioning does not relax that firewall boundary.

## Provision

The provisioner backs up `/conf/config.xml`, installs the endpoint, creates or
reuses the narrow account, writes HA secrets atomically, validates HA, restarts
Core and runs live positive and negative tests:

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_opnsense_readonly.sh
```

Re-running is idempotent while the matching Keychain items remain available.
The live test verifies a successful status GET, `403` for the user-management
API, `405` for POST on the companion endpoint, and the exact account privilege:

```bash
scripts/test_opnsense_live.sh
```

Because the companion files are outside an OPNsense package, rerun the
provisioner after a major OPNsense upgrade. The account remains inert if those
files are absent because its sole ACL identifier then maps to no route.

## Home Assistant behavior

`sensor.muse_opnsense_gateway_feed` polls every 30 seconds.
`sensor.muse_internet_status` normalizes all present and future Starlink, 5G
and fiber gateways to `normal`, `degraded`, `offline` or `unavailable`.
`binary_sensor.muse_opnsense_data_stale` refuses narration after 120 seconds
without a fresh router timestamp. The narrator lists gateway names and states,
but exposes no button, switch or mutable service. Assist receives only the
normalized Internet fact and the bounded house-narration script; the raw feed
and stale guard remain internal.

## Rollback

1. Remove the Muse controller and ACL directories under
   `/usr/local/opnsense/mvc/app/{controllers,models}/OPNsense/Muse`.
2. Remove `homeassistant_muse` in **System > Access > Users**, or restore the
   timestamped `/conf/config.xml.pre-muse-readonly-*` backup.
3. Remove the REST block and normalized OPNsense entities from the HA package,
   validate configuration, then restart Core.
4. Delete the two `OPNsense Home Assistant API` Keychain items.

The implementation follows the official [OPNsense API authentication and
least-privilege guidance](https://docs.opnsense.org/development/api.html) and
Home Assistant's [REST integration](https://www.home-assistant.io/integrations/rest/).
