#!/usr/bin/env bash
set -euo pipefail

: "${PVE_HOST:?Set PVE_HOST, for example user@proxmox-host}"

CHANNEL="${1:?Usage: promote_firmware_channel.sh beta|stable QUALIFICATION_RECORD}"
QUALIFICATION_RECORD="${2:?Provide the reviewed qualification record path}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/release}"

if [[ "$CHANNEL" != "beta" && "$CHANNEL" != "stable" ]]; then
  echo "Only beta or stable can be promoted explicitly." >&2
  exit 2
fi
if [[ ! -s "$QUALIFICATION_RECORD" ]]; then
  echo "Qualification record is missing or empty: $QUALIFICATION_RECORD" >&2
  exit 2
fi
if ! grep -Eq '^## (Canary validation|Runtime validation|Qualification)' \
  "$QUALIFICATION_RECORD"; then
  echo "Qualification record has no recognized validation section." >&2
  exit 2
fi

allow_variable="ALLOW_$(printf '%s' "$CHANNEL" | tr '[:lower:]' '[:upper:]')"
env "$allow_variable=1" CHANNEL="$CHANNEL" OUTPUT_DIR="$OUTPUT_DIR" \
  "$SCRIPT_DIR/package_firmware.sh"

version="$(jq -r .version "$OUTPUT_DIR/manifest-$CHANNEL.json")"
artifact="$OUTPUT_DIR/muse-luxe-$version.ota.bin"
manifest="$OUTPUT_DIR/manifest-$CHANNEL.json"

PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$artifact" "muse-luxe/channels/$CHANNEL/firmware.ota.bin"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$manifest" "muse-luxe/channels/$CHANNEL/manifest.json"

echo "Promoted $version to the private $CHANNEL channel."
