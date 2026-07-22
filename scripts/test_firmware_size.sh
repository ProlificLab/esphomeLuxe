#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT

target_bytes=1889402
truncate -s "$target_bytes" "$temporary/at-target.bin"
FIRMWARE="$temporary/at-target.bin" REPORT="$temporary/at-target.txt" \
  "$root/scripts/check_firmware_size.sh" >/dev/null

truncate -s "$((target_bytes + 1))" "$temporary/over-target.bin"
if FIRMWARE="$temporary/over-target.bin" REPORT="$temporary/over-target.txt" \
  "$root/scripts/check_firmware_size.sh" >/dev/null 2>&1; then
  echo "Firmware one byte over target was accepted" >&2
  exit 1
fi

if FIRMWARE="$temporary/missing.bin" REPORT="$temporary/missing.txt" \
  "$root/scripts/check_firmware_size.sh" >/dev/null 2>&1; then
  echo "Missing firmware was accepted" >&2
  exit 1
fi

echo "Firmware size boundary tests passed."
