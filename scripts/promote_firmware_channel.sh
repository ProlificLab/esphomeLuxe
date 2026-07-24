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
if [[ -n "$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal)" ]]; then
  echo "Promotion requires a clean Git worktree." >&2
  exit 2
fi

target_ref="${RELEASE_TARGET_REF:-HEAD}"
source_commit="$(git -C "$ROOT_DIR" rev-parse --verify "$target_ref^{commit}")"
source_epoch="$("$SCRIPT_DIR/source_date_epoch.sh" "$source_commit")"
head_commit="$(git -C "$ROOT_DIR" rev-parse --verify 'HEAD^{commit}')"
if [[ "$source_commit" != "$head_commit" ]]; then
  echo "Promotion target must be the currently checked-out commit." >&2
  exit 2
fi

config="${CONFIG:-luxe_microWW.yaml}"
esphome_image="esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0"
docker run --rm -e SOURCE_DATE_EPOCH="$source_epoch" \
  -v "$ROOT_DIR":/config -w /config "$esphome_image" \
  clean "$config"
docker run --rm -e SOURCE_DATE_EPOCH="$source_epoch" \
  -v "$ROOT_DIR":/config -w /config "$esphome_image" \
  compile "$config"

allow_variable="ALLOW_$(printf '%s' "$CHANNEL" | tr '[:lower:]' '[:upper:]')"
env "$allow_variable=1" CHANNEL="$CHANNEL" OUTPUT_DIR="$OUTPUT_DIR" \
  "$SCRIPT_DIR/package_firmware.sh"

version="$(jq -r .version "$OUTPUT_DIR/manifest-$CHANNEL.json")"
artifact="$OUTPUT_DIR/muse-luxe-$version.ota.bin"
manifest="$OUTPUT_DIR/manifest-$CHANNEL.json"
qualification="$OUTPUT_DIR/qualification-$version.json"

"$SCRIPT_DIR/verify_release.sh" "$manifest" "$artifact"
python3 "$SCRIPT_DIR/check_qualification_record.py" \
  --record "$QUALIFICATION_RECORD" \
  --manifest "$manifest" \
  --artifact "$artifact" \
  --channel "$CHANNEL" \
  --source-commit "$source_commit"
cp "$QUALIFICATION_RECORD" "$qualification"

report_args=(
  --target "$source_commit"
  --output-markdown "$OUTPUT_DIR/CHANGELOG.md"
  --output-json "$OUTPUT_DIR/dependency-diff.json"
)
if [[ -n "${RELEASE_BASE_REF:-}" ]]; then
  report_args+=(--base "$RELEASE_BASE_REF")
fi
python3 "$SCRIPT_DIR/report_release_changes.py" "${report_args[@]}"

PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$artifact" "muse-luxe/channels/$CHANNEL/firmware-$version.ota.bin"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$qualification" "muse-luxe/channels/$CHANNEL/qualification-$version.json"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$OUTPUT_DIR/CHANGELOG.md" "muse-luxe/channels/$CHANNEL/CHANGELOG-$version.md"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$OUTPUT_DIR/dependency-diff.json" \
  "muse-luxe/channels/$CHANNEL/dependency-diff-$version.json"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$OUTPUT_DIR/build-metadata.json" \
  "muse-luxe/channels/$CHANNEL/build-metadata-$version.json"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$OUTPUT_DIR/MD5SUMS" "muse-luxe/channels/$CHANNEL/MD5SUMS-$version"
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$OUTPUT_DIR/SHA256SUMS" "muse-luxe/channels/$CHANNEL/SHA256SUMS-$version"
# The manifest is the activation point and must remain the final publication.
PVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" \
  "$manifest" "muse-luxe/channels/$CHANNEL/manifest.json"

echo "Promoted $version to the private $CHANNEL channel."
