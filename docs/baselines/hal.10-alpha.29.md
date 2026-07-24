# Distribution baseline `hal.10-alpha.29`

## Scope

- Derive the complete source record from exact OTA, clean Git and five logs.
- Validate and atomically publish it without trusting manually entered metrics.

## Safety contract

- Clean full source commit, release-formatted version and exact OTA SHA/size.
- Canonical successful CI run/job bound to that source commit.
- Two build logs contain the exact OTA hash; size log equals recomputation.
- Secret report compares at least three real values with no findings.
- Five logs are distinct, non-empty, internal and hash-bound.
- Validation precedes an atomic no-clobber link; failures leave no final record.

## Validation

- Five sealer fixtures cover exact derivation, overwrite refusal, CI/build drift,
  size/audit failure and external logs.
- Seven shared source-record fixtures include standalone version-format refusal.
- No build, network, credential generation or device action occurs in sealing.

## Source evidence

- Atomic source sealer SHA-256:
  `c97d633b5f92b81bc8675dc7c663d7be6a825fa69d0866f5f8760df76c958a5e`.
- Sealer fixtures SHA-256:
  `fe1dfc5ed7c0b883b450ef472282c5b67c9ce4eefa09800e837df6e41e5f69a4`.
- Shared source validator SHA-256:
  `a951a8ac86d574c014c6efac143c7588e8ab160c9e61638ddadcab8f2705f799`.
- Shared validator fixtures SHA-256:
  `c5ed95cf36f9cdd3b878721af9a6272ae556b9dc5477127231371418640f5bc2`.
- Operator guide SHA-256:
  `7b9aed18e5b5ecfb8f8494a70ea36d5678ec486dc8253f2bff52b44e830de852`.
