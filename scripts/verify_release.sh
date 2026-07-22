#!/usr/bin/env bash
set -euo pipefail

MANIFEST="${1:?Usage: verify_release.sh MANIFEST ARTIFACT}"
ARTIFACT="${2:?Usage: verify_release.sh MANIFEST ARTIFACT}"

[[ -s "$MANIFEST" ]] || { echo "Manifest is missing or empty." >&2; exit 2; }
[[ -s "$ARTIFACT" ]] || { echo "Artifact is missing or empty." >&2; exit 2; }

jq -e '.name == "raspiaudio.voice-assistant" and
       (.channel | IN("development", "beta", "stable")) and
       (.version | type == "string") and
       (.builds | length == 1) and
       (.builds[0].chipFamily == "ESP32") and
       (.builds[0].ota.offset == 0) and
       (.builds[0].ota.md5 | test("^[0-9a-f]{32}$")) and
       (.builds[0].ota.path | type == "string")' "$MANIFEST" >/dev/null

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
channel="$(jq -r .channel "$MANIFEST")"
if [[ ! "$version" =~ ^[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+$ ]]; then
  echo "Manifest project version is invalid." >&2
  exit 1
fi
[[ "$(basename "$ARTIFACT")" == "muse-luxe-$version.ota.bin" ]] || {
  echo "Artifact filename does not match manifest version." >&2
  exit 1
}
if [[ "$channel" == "stable" &&
      ( "$version" == *alpha* || "$version" == *beta* || "$version" == *rc* ) ]]; then
  echo "Prerelease version cannot use the stable channel." >&2
  exit 1
fi
if [[ "$channel" == "beta" && "$version" == *alpha* ]]; then
  echo "Alpha version cannot use the beta channel." >&2
  exit 1
fi
if [[ "$channel" == "development" ]]; then
  expected_path="http://10.10.30.159:8123/local/muse-luxe/channels/development/firmware.ota.bin"
else
  expected_path="http://10.10.30.159:8123/local/muse-luxe/channels/$channel/firmware-$version.ota.bin"
fi
actual_path="$(jq -r '.builds[0].ota.path' "$MANIFEST")"
if [[ "$actual_path" != "$expected_path" ]]; then
  echo "Manifest OTA path is not the expected private versioned path." >&2
  exit 1
fi
echo "Verified $version ($channel) release artifact."
