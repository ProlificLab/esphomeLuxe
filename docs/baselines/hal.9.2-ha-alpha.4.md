# hal.9.2 Home Assistant alpha 4 baseline

## Scope

- OPNsense 26.7 companion endpoint exposing gateway status through GET only.
- Dedicated `homeassistant_muse` API identity with only
  `page-muse-readonly`; no standard gateway, routing or firewall privilege.
- Home Assistant REST polling every 30 seconds and a 120-second stale guard.
- Multi-WAN normalization ready for Starlink, 5G and fiber gateway records.
- Combined deterministic Victron, Proxmox and Internet narration.
- Static policy and live negative tests for forbidden API access and POST.

## Target evidence

- OPNsense version: `26.7` on `192.168.1.1` / `10.10.30.1`.
- Home Assistant Core: `2026.7.2`.
- Active gateways: `WAN_DHCP` and `WAN_DHCP6`, both Online.
- Controller method: `GET /api/muse/status/gateways`.
- Credential privilege: exactly `page-muse-readonly`; effective ACL masks: 1,
  exactly `api/muse/status/gateways`, with no group-derived authority.
- User-management API with this credential: `403` verified.
- POST to the companion endpoint: `405` verified.
- Live endpoint: 2 gateways; Home Assistant normalized state `normal`, online
  count 2, stale guard off and controls exposed 0.
- Assist exposure: normalized Internet fact 1, bounded narration script 1,
  OPNsense controls 0; raw feed and stale guard hidden.
- HA configuration check: passed before both controlled restarts.
- HA package SHA-256:
  `6be06749fbf7bd529b2a4145d0bfcb67f02d687d85ed69b69d9a197d0c584b5d`.
- OPNsense controller SHA-256:
  `8f4ad81df407358529b8ee214e1a7d273b86f72f7171841ae1076cd424a9d8b5`.
- OPNsense ACL SHA-256:
  `c5a71c7dae1a684b040d3d77812d20c1af7d37a4665c1f600dbe1647ffe2de4d`.
- OPNsense provision model SHA-256:
  `73f7f0f891333cf1f65e506a5a3554c843350497690170e3e44f5f4392081e15`.
- End-to-end provisioner SHA-256:
  `f110e950c617541ff39040a5052a0f26356df36b22d5b833dc4639a68711f916`.
- Assist hardener SHA-256:
  `b96ad3c831c0bf3ce560b6b4101d253b08347d9043ea7ff90af23a1ecffb61c6`.
- HA live test SHA-256:
  `9aaa2ff09b7b96c6d706575a33435851b9a5f3442ecd6c1a52a7f1ac3103c9ab`.
- Direct OPNsense live test SHA-256:
  `9c0ae86d97dde7bd74e0c4eb785e0abec43d4f75b0b6149548b90bf57e2a1513`.

## Open gates

- Install the future 5G and fiber uplinks in OPNsense before validating real
  degraded and failover states.
- Replace the self-signed OPNsense WebGUI certificate or distribute its CA to
  Home Assistant before enabling TLS verification.
- Add authenticated Frigate camera entities before narrating individual camera
  availability or offering snapshots.
