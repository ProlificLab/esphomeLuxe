#!/usr/bin/env bash
set -euo pipefail

usage="Usage: collect_source_qualification.sh OUTPUT_DIR VERSION CI_JSON REVIEWER"
OUTPUT_DIR="${1:?$usage}"
VERSION="${2:?$usage}"
CI_JSON="${3:?$usage}"
REVIEWER="${4:?$usage}"
CONFIG="${CONFIG:-luxe_microWW.yaml}"
SECRETS="${SECRETS:-secrets.yaml}"
IMAGE="esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
FIRMWARE="$ROOT/.esphome/build/muse-luxe/.pioenvs/muse-luxe/firmware.ota.bin"
cd "$ROOT"

config_version="$(sed -n 's/^[[:space:]]*version: "\([^"]*\)"/\1/p' "$CONFIG" | head -n 1)"
if [[ ! "$VERSION" =~ ^[0-9]{4}\.[0-9]+\.[0-9]+-[A-Za-z0-9.-]+$ || "$VERSION" != "$config_version" ]]; then
  echo "Requested version must exactly match the release-formatted config version." >&2; exit 1
fi

if [[ -n "$(git -C "$ROOT" status --porcelain --untracked-files=normal)" ]]; then
  echo "Source collection requires a clean Git worktree." >&2; exit 1
fi
if [[ -e "$OUTPUT_DIR" || ! -d "$(dirname "$OUTPUT_DIR")" ]]; then
  echo "Output must be a new directory under an existing parent." >&2; exit 1
fi
if [[ ! -f "$SECRETS" || -L "$SECRETS" ]]; then
  echo "Private secrets file is missing or a symlink." >&2; exit 1
fi
secret_mode="$(stat -f '%Lp' "$SECRETS" 2>/dev/null || stat -c '%a' "$SECRETS")"
[[ "$secret_mode" == "600" ]] || { echo "Private secrets permissions must be 0600." >&2; exit 1; }
mkdir -m 700 "$OUTPUT_DIR"
trap 'status=$?; if (( status != 0 )); then rm -rf "$OUTPUT_DIR"; fi' EXIT
cp "$CI_JSON" "$OUTPUT_DIR/ci.log"
chmod 600 "$OUTPUT_DIR/ci.log"
python3 "$SCRIPT_DIR/audit_tracked_secrets.py" --private-secrets "$SECRETS" \
  --require-private-keys 3 --output "$OUTPUT_DIR/secrets-audit.log" >/dev/null

build_once() {
  local log="$1"
  docker run --rm -v "$ROOT:/config" -w /config "$IMAGE" clean "$CONFIG" >>"$log" 2>&1
  docker run --rm -v "$ROOT:/config" -w /config "$IMAGE" compile "$CONFIG" >>"$log" 2>&1
  local sha
  sha="$(shasum -a 256 "$FIRMWARE" | awk '{print $1}')"
  printf 'OTA SHA256=%s\n' "$sha" >>"$log"
  printf '%s' "$sha"
}

first_sha="$(build_once "$OUTPUT_DIR/build-first.log")"
cp "$FIRMWARE" "$OUTPUT_DIR/first.ota.bin"
second_sha="$(build_once "$OUTPUT_DIR/build-second.log")"
if [[ "$first_sha" != "$second_sha" ]]; then
  echo "Independent pinned builds are not reproducible." >&2; exit 1
fi
artifact="$OUTPUT_DIR/muse-luxe-$VERSION.ota.bin"
cp "$FIRMWARE" "$artifact"
chmod 600 "$OUTPUT_DIR"/*
FIRMWARE="$artifact" REPORT="$OUTPUT_DIR/firmware-size.log" \
  "$SCRIPT_DIR/check_firmware_size.sh" >/dev/null
python3 "$SCRIPT_DIR/check_private_log_disclosure.py" --private-secrets "$SECRETS" \
  "$OUTPUT_DIR/ci.log" "$OUTPUT_DIR/build-first.log" "$OUTPUT_DIR/build-second.log" \
  "$OUTPUT_DIR/firmware-size.log" "$OUTPUT_DIR/secrets-audit.log" >/dev/null
python3 "$SCRIPT_DIR/seal_source_qualification_evidence.py" \
  "$OUTPUT_DIR/source-$VERSION.json" "$artifact" "$VERSION" \
  --logs-dir "$OUTPUT_DIR" --reviewer "$REVIEWER"
echo "Collected and sealed two-build source qualification in $OUTPUT_DIR."
