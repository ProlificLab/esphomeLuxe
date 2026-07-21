#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-luxe_microWW.yaml}"
FIRMWARE="${FIRMWARE:-.esphome/build/muse-luxe/.pioenvs/muse-luxe/firmware.ota.bin}"
OUTPUT_DIR="${OUTPUT_DIR:-release}"
OTA_URL="${OTA_URL:-http://10.10.30.159:8123/local/muse-luxe/firmware.ota.bin}"

version="${VERSION:-$(sed -n 's/^[[:space:]]*version: "\([^"]*\)"/\1/p' "$CONFIG" | head -n 1)}"
if [[ -z "$version" || ! "$version" =~ ^[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+$ ]]; then
  echo "Unable to determine a valid project version from $CONFIG" >&2
  exit 2
fi
if [[ ! -f "$FIRMWARE" ]]; then
  echo "Firmware not found: $FIRMWARE" >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"
artifact="$OUTPUT_DIR/muse-luxe-${version}.ota.bin"
cp "$FIRMWARE" "$artifact"

if command -v md5 >/dev/null 2>&1; then
  md5_hash="$(md5 -q "$artifact")"
else
  md5_hash="$(md5sum "$artifact" | awk '{print $1}')"
fi
if command -v shasum >/dev/null 2>&1; then
  sha256_hash="$(shasum -a 256 "$artifact" | awk '{print $1}')"
else
  sha256_hash="$(sha256sum "$artifact" | awk '{print $1}')"
fi

printf '%s  %s\n' "$md5_hash" "$(basename "$artifact")" > "$OUTPUT_DIR/MD5SUMS"
printf '%s  %s\n' "$sha256_hash" "$(basename "$artifact")" > "$OUTPUT_DIR/SHA256SUMS"
cat > "$OUTPUT_DIR/manifest.json" <<EOF
{
  "name": "raspiaudio.voice-assistant",
  "version": "$version",
  "builds": [
    {
      "chipFamily": "ESP32",
      "ota": {
        "md5": "$md5_hash",
        "path": "$OTA_URL",
        "offset": 0,
        "summary": "ProlificLab Muse Luxe $version"
      }
    }
  ]
}
EOF

printf 'Packaged %s\nMD5 %s\nSHA256 %s\n' "$artifact" "$md5_hash" "$sha256_hash"
