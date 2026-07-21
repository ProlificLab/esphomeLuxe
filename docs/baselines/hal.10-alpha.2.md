# hal.10 alpha 2 baseline

## Scope

- Deterministic changelog generated from two Git commits.
- Changed files grouped into firmware, Home Assistant, tooling/CI,
  documentation and other subsystems.
- Machine-readable inventory and diff for pinned build, framework, wake-word
  and CI dependencies.
- Pull-request base SHA and previous-tag comparison supported.
- First release without tags compared against the empty Git tree.

## Validation

- Reporter unit test runs in an isolated temporary Git repository.
- Python syntax and shell syntax remain checked by CI.
- Markdown and JSON reports are included in the existing release artifact.

## Open gates

- Complete the running 24-hour endurance campaign.
- Validate a second physical Muse Luxe before family audio transfer promotion.
- Exercise and document rollback from the future first `stable` tag.
