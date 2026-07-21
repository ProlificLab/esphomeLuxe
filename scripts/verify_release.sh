#!/usr/bin/env bash
set -euo pipefail

MANIFEST="${1:?Usage: verify_release.sh MANIFEST ARTIFACT}"
ARTIFACT="${2:?Usage: verify_release.sh MANIFEST ARTIFACT}"

jq -e '.name == "raspiaudio.voice-assistant" and
       (.channel | IN("development", "beta", "stable")) and
       (.version | type == "string") and
       (.builds | length == 1) and
       (.builds[0].chipFamily == "ESP32")' "$MANIFEST" >/dev/null

expected_md5="$(jq -r '.builds[0].ota.md5' "$MANIFEST")"
if command -v md5 >/dev/null 2>&1; then
  actual_md5="$(md5 -q "$ARTIFACT")"
else
  actual_md5="$(md5sum "$ARTIFACT" | awk '{print $1}')"
fi
if [[ "$actual_md5" != "$expected_md5" ]]; then
  echo "Manifest MD5 does not match artifact." >&2
  exit 1
fi

version="$(jq -r .version "$MANIFEST")"
[[ "$(basename "$ARTIFACT")" == "muse-luxe-$version.ota.bin" ]] || {
  echo "Artifact filename does not match manifest version." >&2
  exit 1
}
echo "Verified $version ($(jq -r .channel "$MANIFEST")) release artifact."
