#!/usr/bin/env bash
set -euo pipefail

MANIFEST="${1:-manifest_update.json}"
jq -e '.version == "2025.3.1-hal.6" and
       .builds[0].ota.md5 == "cedf966640caccbabba098bcf22f7645" and
       .builds[0].ota.path ==
         "http://10.10.30.159:8123/local/muse-luxe/firmware.ota.bin"' \
  "$MANIFEST" >/dev/null || {
  echo "Production rollback manifest changed without stable promotion." >&2
  exit 1
}
echo "Production manifest remains pinned to hal.6."
