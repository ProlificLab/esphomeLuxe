# Distribution baseline `hal.10-alpha.26`

## Scope

- Prepare API, OTA and fallback AP credential rotation entirely offline.
- Preserve unrelated private configuration and isolate the old OTA transition.
- Create private files without overwrite, disclosure or partial output.

## Safety contract

- Current secrets must be an owner-only regular file, no broader than `0600`,
  with all three required keys; source and destination-parent symlinks fail.
- New credentials are independent, differ from current values and use the
  operating-system CSPRNG; the API key decodes to exactly 32 bytes.
- The output directory is new and `0700`; all files are `0600` and synchronized.
- The transition file contains only the old OTA password.
- The manifest and command output contain no credential values and attest zero
  network actions.
- Any failure removes the newly reserved output directory without touching an
  existing destination.

## Validation

- Five offline fixtures cover successful private generation, nondisclosure,
  permissions, preservation, insecure input, overwrite refusal, missing keys,
  collisions, partial-write cleanup and absence of network/device actions.
- No credentials are rotated on the active canary during endurance.

## Source evidence

- Offline preparation tool SHA-256:
  `fb8bae8a55e1e00ad6a2ad104aec32acc1fff309306a7efec2ba7288d97a32ec`.
- Safety fixtures SHA-256:
  `3b91e03e34a75da6638b2cd9ebae6c69f64f7ce1e829b4a15397351510f2a6af`.
- Operator guide SHA-256:
  `4d71a4311ffb61d69d7792d3956e98e09ddfc52eda50bda5a0f75db3e10f8aac`.
