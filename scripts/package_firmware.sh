#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-luxe_microWW.yaml}"
FIRMWARE="${FIRMWARE:-.esphome/build/muse-luxe/.pioenvs/muse-luxe/firmware.ota.bin}"
OUTPUT_DIR="${OUTPUT_DIR:-release}"
CHANNEL="${CHANNEL:-development}"
OTA_URL="${OTA_URL:-}"

case "$CHANNEL" in
  development | beta | stable) ;;
  *) echo "Invalid release channel: $CHANNEL" >&2; exit 2 ;;
esac

version="${VERSION:-$(sed -n 's/^[[:space:]]*version: "\([^"]*\)"/\1/p' "$CONFIG" | head -n 1)}"
if [[ -z "$version" || ! "$version" =~ ^[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+$ ]]; then
  echo "Unable to determine a valid project version from $CONFIG" >&2
  exit 2
fi
if [[ -z "$OTA_URL" ]]; then
  if [[ "$CHANNEL" == "development" ]]; then
    OTA_URL="http://10.10.30.159:8123/local/muse-luxe/channels/$CHANNEL/firmware.ota.bin"
  else
    OTA_URL="http://10.10.30.159:8123/local/muse-luxe/channels/$CHANNEL/firmware-$version.ota.bin"
  fi
fi
if [[ ! -f "$FIRMWARE" ]]; then
  echo "Firmware not found: $FIRMWARE" >&2
  exit 2
fi
if [[ "$CHANNEL" == "stable" ]]; then
  if [[ "${ALLOW_STABLE:-0}" != "1" ]]; then
    echo "Stable packaging requires ALLOW_STABLE=1 after physical qualification." >&2
    exit 2
  fi
  if [[ "$version" == *alpha* || "$version" == *beta* || "$version" == *rc* ]]; then
    echo "Prerelease version cannot be packaged into the stable channel." >&2
    exit 2
  fi
fi
if [[ "$CHANNEL" == "beta" && "${ALLOW_BETA:-0}" != "1" ]]; then
  echo "Beta packaging requires ALLOW_BETA=1 after canary qualification." >&2
  exit 2
fi
if [[ "$CHANNEL" == "beta" && "$version" == *alpha* ]]; then
  echo "Alpha version cannot be packaged into the beta channel." >&2
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
manifest="$OUTPUT_DIR/manifest-$CHANNEL.json"
cat > "$manifest" <<EOF
{
  "name": "raspiaudio.voice-assistant",
  "version": "$version",
  "channel": "$CHANNEL",
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

cat > "$OUTPUT_DIR/build-metadata.json" <<EOF
{
  "version": "$version",
  "channel": "$CHANNEL",
  "source_commit": "$(git rev-parse HEAD)",
  "config": "$CONFIG",
  "artifact": "$(basename "$artifact")",
  "size_bytes": $(wc -c < "$artifact" | tr -d ' '),
  "md5": "$md5_hash",
  "sha256": "$sha256_hash",
  "esphome_image": "esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0",
  "esp_idf": "5.4.2"
}
EOF

printf 'Packaged %s for %s\nManifest %s\nMD5 %s\nSHA256 %s\n' \
  "$artifact" "$CHANNEL" "$manifest" "$md5_hash" "$sha256_hash"
