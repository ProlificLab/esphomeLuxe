# Distribution baseline `hal.10-alpha.7`

## Scope

- Keep the existing 13 beta and 33 stable gate names.
- Replace free-form `physical_controls` evidence with a SHA-256-bound relative
  JSON path.
- Resolve the record below the qualification directory and reject traversal,
  missing files or hash drift through the shared evidence resolver.
- Bind physical observations to the exact candidate version and OTA SHA-256.
- Revalidate the closed ten-case checklist during beta and stable promotion.

## Validation

- Standalone physical evidence positive and negative fixtures: passed.
- Positive beta and stable qualification fixtures include bound physical records.
- Tampered and unbound physical records: rejected.
- Existing mode, endurance, promotion and release guards remain unchanged.

## Open gates

The checked-in example remains entirely false and contains placeholders. It is
not physical evidence; promotion stays blocked until a recent real record is
reviewed beside the candidate artifact.

## Source evidence

- Qualification checker SHA-256:
  `aabf03a8ca9f551dd7614fe6fefd15f8b886e2e9975c38abf7c790b4086f79bb`.
- Qualification fixtures SHA-256:
  `591bf0a8969cb2fe841adb72c961c0f053c9ddf137dcc1e6e4a730e5331a5595`.
- Qualification template SHA-256:
  `ad5cec2640b72baad8c7295f1ea62b659057bd2023bd6b309ca0f6d0926f7f1f`.
