# Distribution baseline `hal.10-alpha.27`

## Scope

- Validate the prepared credential bundle before any transition action.
- Return only safe counts and status, never private values or fingerprints.

## Safety contract

- Directory and three files require exact owner, type and private permissions.
- Manifest schema, fixed filenames, preparation state and 30-day age are closed.
- Three new independent non-fixture credentials meet API, OTA and WPA bounds.
- Transition contains exactly one old OTA credential distinct from the new one.
- Symlinks, path drift, zero API material and any prior network action fail.

## Validation

- Five fixtures cover valid nondisclosing output, permissions, symlinks,
  manifest drift/age, weak/duplicate/zero values and transition isolation.
- The checker performs no network, device, build or installation action.

## Source evidence

- Bundle checker SHA-256:
  `e62830a144e009c5d7f49bbd519aee3e9288c5a6f809faa217bd89e494ee78be`.
- Checker fixtures SHA-256:
  `a5311e5f0cd50918c16604fbfcf0ed1d928ea1e2ccf97da1f3b771b1dc4c5107`.
- Updated operator guide SHA-256:
  `2c06f66d4537ac054ed0556bf0a238145be42ab1ec4883276c7dfbabdaa1ea31`.
