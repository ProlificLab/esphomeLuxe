#!/usr/bin/env python3
"""Unit tests for the Proxmox audit-only permission validator."""

from __future__ import annotations

import unittest

from check_proxmox_permissions import validate


class ProxmoxPermissionsTest(unittest.TestCase):
    def test_accepts_audit_only_permissions(self) -> None:
        granted = validate(
            {"/": {"Sys.Audit": 1, "VM.Audit": 1, "Datastore.Audit": 1}}
        )
        self.assertEqual(granted, {"Sys.Audit", "VM.Audit", "Datastore.Audit"})

    def test_rejects_write_permission(self) -> None:
        with self.assertRaisesRegex(ValueError, "Non-audit"):
            validate({"/": {"Sys.Audit": 1, "VM.Audit": 1, "VM.PowerMgmt": 1}})

    def test_requires_vm_and_system_audit(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required"):
            validate({"/": {"Datastore.Audit": 1}})


if __name__ == "__main__":
    unittest.main()
