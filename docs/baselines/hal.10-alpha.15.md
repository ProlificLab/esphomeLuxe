# Distribution baseline `hal.10-alpha.15`

## Scope

- Keep 13 beta and 33 stable gate names unchanged.
- Require stable `announcement_routing_queue` evidence as a hash-bound path.
- Bind the loaded record to candidate version and OTA SHA-256.
- Recompute the exact base Home Assistant package hash from source.
- Reject open targets, stale queues, missing error restoration and external
  delivery.

## Validation

- Standalone announcement evidence positive and negative fixtures: passed.
- Positive stable qualification includes the bound candidate/package record.
- Tampered and unbound announcement records: rejected.
- Existing beta and previously structured stable bindings remain active.

## Open gates

The source and example are not physical announcement evidence. Stable remains
blocked until the exact candidate passes the end-to-end protocol.

## Source evidence

- Qualification checker SHA-256:
  `c3de329a73e2da362603247f8f89b507e2f964992b6c4800eb06240d151a4dc8`.
- Qualification fixtures SHA-256:
  `1a4fa4b98c78cb6e8ac362efc6260d3a573287cefa86b12ff3cef252addb305e`.
- Qualification template SHA-256:
  `4e01110d1610eeb89ff32c360f384eb28e8aa6a13104450536f073a441132c49`.
