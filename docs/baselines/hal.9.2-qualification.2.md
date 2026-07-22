# Source baseline `hal.9.2-qualification.2`

## Scope

- Four normalized domains remain deterministic and read-only.
- Stale thresholds are exact: Frigate 30, OPNsense 120, Proxmox 300 and Victron
  300 seconds.
- Victron, Proxmox and Frigate use the oldest required source, never the newest.
- Twenty-three closed scenarios cover fresh, stale, recovery, ACL, narration
  and final cleanup behavior.
- Candidate, OTA, package and four infrastructure policy hashes are exact.

## Validation

- Static source contract and five unsafe mutations: passed and rejected.
- Complete house-intelligence evidence fixture: passed.
- Candidate binding, runtime, scenarios, metrics, booleans, final state and time
  negative fixtures: rejected.
- No physical infrastructure or narration behavior is claimed here.

## Open gates

Run each telemetry interruption separately after endurance and in a maintenance
window. The example stays failed until all real observations are complete.

## Source evidence

- House-intelligence safety checker SHA-256:
  `fdac6c71c0c3bfd2ff53ac8aa5172bf42d6e5d430c528cb09ce08e1eea8121f6`.
- Safety negative fixtures SHA-256:
  `1b192f0017827c4fd3026bd4abd50635a8e528a204868b28bb79f483e5d54f01`.
- Evidence validator SHA-256:
  `f41a0c29d7fb30d5aa8b0307d4856dd60b8c3bcfe814588d786ac89a26beb5cf`.
- Evidence positive and negative fixtures SHA-256:
  `06614db5093b464b8ca99ed2102404c8fa6b2cdaf2314e5daf14d8f647489eb7`.
- Unqualified example record SHA-256:
  `33a9b313208a76b3eae3f953b12d1e1c97dcb3a83dc6a46704efdd673bdaf7f4`.
