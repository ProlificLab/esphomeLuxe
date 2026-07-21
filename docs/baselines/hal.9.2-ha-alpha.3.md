# hal.9.2 Home Assistant alpha 3 baseline

## Scope

- Official Proxmox VE integration authenticated by a dedicated PVE user and a
  privilege-separated API token.
- `PVEAuditor` at `/` for the user group and token; no PAM/root credential.
- Effective JSON permission allowlist requiring audit-only privileges.
- All generated Proxmox buttons disabled and all entities excluded from Assist.
- Normalized node, HAOS, Frigate, LibreNMS and Ollama facts with five-minute
  telemetry freshness.
- Combined deterministic Victron/Proxmox narration; no infrastructure action.
- CI allowlist for narration actions and unsafe negative fixtures.

## Target evidence

- Proxmox VE `9.2.0`, manager `9.2.4`.
- Home Assistant Core `2026.7.2`.
- Config entry: `01KY38H59ETG108C9MER8E2D14`.
- ACLs: group `homeassistant` and token
  `homeassistant@pve!homeassistant`, role `PVEAuditor`, path `/`, propagate on.
- Effective unique privileges: 7, all ending in `.Audit`.
- Integration entities: 118; control buttons disabled: 29; Assist-exposed: 0.
- Live state: node online, HAOS running, Frigate running, LibreNMS running,
  Ollama stopped by design, normalized status normal and stale guard off.
- Physical combined narration: playback observed and returned to `idle`.
- Home Assistant configuration check: passed.
- House-intelligence package SHA-256:
  `28975f8cb072e750cc7c289f215dc662eae7fca10e713912b0b9d19092b5a489`.
- HA config-flow helper SHA-256:
  `d0e8a5fcd8ffaa38963b4f4fc0c7d104869026132d6a53333275b029f97b82e0`.
- Entity hardener SHA-256:
  `4c3a86b3dc1fa74c81960f1abf08da271fe53d3ac7a98da9828fe0fc0c59aa21`.
- Provisioner SHA-256:
  `8d43ff49751843538ef6b1f3dc6d65d699ef506e4c808b26ced98cd5feb368ab`.
- End-to-end test SHA-256:
  `d47870a865b8e166390b72925c56f769a95647f33fb3a58f13fe426eb6776ef4`.

## Open gates

- Add OPNsense read-only entities before narrating Internet uplinks.
- Add authenticated Frigate camera entities before narrating individual camera
  availability or offering snapshots.
- Define which guest is meant by the server-shutdown routine before using a
  Proxmox status as its completion proof.
- Review the existing Victron integration startup warning about blocking TLS
  certificate initialization independently of this package.
