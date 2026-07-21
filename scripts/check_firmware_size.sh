#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR="${BUILD_DIR:-.esphome/build/muse-luxe}"
FIRMWARE="${FIRMWARE:-$BUILD_DIR/.pioenvs/muse-luxe/firmware.ota.bin}"
REPORT="${REPORT:-firmware-size.txt}"

# The OTA partition is 1,984 KiB. hal.6 is the regression baseline until hal.7
# is promoted; the lower target leaves room for user-facing features.
PARTITION_BYTES=2031616
BASELINE_BYTES=1948144
TARGET_PERCENT=93
HARD_PERCENT=97

if [[ ! -f "$FIRMWARE" ]]; then
  echo "Firmware not found: $FIRMWARE" >&2
  exit 2
fi

size_bytes="$(wc -c < "$FIRMWARE" | tr -d ' ')"
percent_x10="$((size_bytes * 1000 / PARTITION_BYTES))"
target_bytes="$((PARTITION_BYTES * TARGET_PERCENT / 100))"
hard_bytes="$((PARTITION_BYTES * HARD_PERCENT / 100))"

mkdir -p "$(dirname "$REPORT")"
{
  printf 'firmware=%s\n' "$FIRMWARE"
  printf 'size_bytes=%s\n' "$size_bytes"
  printf 'partition_bytes=%s\n' "$PARTITION_BYTES"
  printf 'usage_percent=%d.%d\n' "$((percent_x10 / 10))" "$((percent_x10 % 10))"
  printf 'target_percent=%s\n' "$TARGET_PERCENT"
  printf 'hard_percent=%s\n' "$HARD_PERCENT"
  printf 'hal6_baseline_bytes=%s\n' "$BASELINE_BYTES"
} | tee "$REPORT"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '### Firmware size'
    echo
    printf '| OTA bytes | Partition | Usage | hal.6 baseline |\n'
    printf '| ---: | ---: | ---: | ---: |\n'
    printf '| %s | %s | %d.%d%% | %s |\n' \
      "$size_bytes" "$PARTITION_BYTES" "$((percent_x10 / 10))" \
      "$((percent_x10 % 10))" "$BASELINE_BYTES"
  } >> "$GITHUB_STEP_SUMMARY"
fi

if (( size_bytes > hard_bytes )); then
  echo "ERROR: firmware exceeds the ${HARD_PERCENT}% safety ceiling." >&2
  exit 1
fi

if (( size_bytes > BASELINE_BYTES )); then
  echo "ERROR: firmware is larger than the hal.6 regression baseline." >&2
  exit 1
fi

if (( size_bytes > target_bytes )); then
  echo "WARNING: firmware remains above the ${TARGET_PERCENT}% roadmap target." >&2
fi
