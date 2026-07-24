#!/usr/bin/env python3
"""Unit tests for the OPNsense companion endpoint policy."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from check_opnsense_readonly import validate


VALID_CONTROLLER = """
if (!$this->request->isGet()) { return []; }
$backend->configdRun('interface gateways status');
"""
VALID_ACL = """
<acl><page-muse-readonly><patterns>
<pattern>api/muse/status/gateways</pattern>
</patterns></page-muse-readonly></acl>
"""


class OPNsenseReadonlyTest(unittest.TestCase):
    def test_accepts_exact_read_endpoint(self) -> None:
        validate(VALID_CONTROLLER, ET.fromstring(VALID_ACL))

    def test_rejects_wildcard_acl(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact telemetry endpoint"):
            validate(VALID_CONTROLLER, ET.fromstring(VALID_ACL.replace("gateways", "*")))

    def test_rejects_mutable_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Mutable controller primitive"):
            validate(VALID_CONTROLLER + "$backend->configdpRun('write', []);", ET.fromstring(VALID_ACL))


if __name__ == "__main__":
    unittest.main()
