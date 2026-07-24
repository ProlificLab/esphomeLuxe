# Distribution baseline `hal.10-alpha.25`

## Scope

- Bind reproducible build, CI, hard size and tracked-secret audit to one record.
- Bind the stable 93% target to that same source record.
- Hash five distinct raw logs and the candidate version, OTA and source commit.
- Audit real private values against tracked files without exposing the values.

## Safety contract

- Two clean pinned build hashes must equal the reviewed OTA SHA-256.
- CI must be successful for the exact commit and canonical repository/workflow.
- OTA bytes, one-decimal use, 93% target, 97% ceiling and hal.6 baseline are
  independently recalculated.
- At least three non-placeholder private secrets are compared; exact matches,
  known token/key patterns and prohibited tracked files must all remain zero.
- Split, unbound, escaping, duplicate, empty or modified logs are rejected.

## Validation

- Five audit tests prove redaction, exact-value detection, token/key patterns,
  placeholder filtering and atomic reports.
- Seven source-evidence tests cover identity, parsed CI, reproducibility, all budgets,
  private-secret count, findings, logs, schema and expected artifact size.
- Fifty promotion tests cover positive beta/stable records and source-record
  tampering, raw-log tampering, unbound paths and split gates.

## Open gate

The canary currently uses recognizable example API, OTA and fallback AP
credentials. Rotate all three after endurance and before beta; until then the
required real-value audit intentionally cannot pass.

## Source evidence

- Tracked-secret auditor SHA-256:
  `a5cbe0c4b90e9077b1f3ab5e519a1319991ed76576ecf8f09e52af73161e7ece`.
- Auditor fixtures SHA-256:
  `115045293a8b001d298183bb7ebdc0f10568d1459b0d65c7319e6bfe0233eea1`.
- Source-evidence checker SHA-256:
  `054703cb2d9f6f59bdd94d2f1da1925e48e87bfeb564b6bcc638bfe217b3cdd1`.
- Source-evidence fixtures SHA-256:
  `316eac0c540e16965b408f3823310722e65af880324fac2201bd396f829e84c6`.
- Source-record template SHA-256:
  `b41c9274875f1da8eafd3a706ba526ecece8f4da4f746635ff6ff961cd8e337d`.
- Promotion checker SHA-256:
  `52ab0995cbf886bcc203c9249d162877ceb867d16b647a400b6bc63f294bbe6b`.
- Promotion fixtures SHA-256:
  `6cfa2043a804a93ffad741ec36ecdbe3239ddf1da8de36a562acdceecada07ec`.
- Operator guide SHA-256:
  `6c372dd00597865962a0a689497c9a1821f2a21d1928640e7f817f681976cac7`.
