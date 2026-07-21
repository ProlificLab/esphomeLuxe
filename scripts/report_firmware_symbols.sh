#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-esphome/esphome@sha256:def6336d7d587f9b056893e86d1cfedfe86db360188221e9f122804872d385b0}"
ELF="${ELF:-.esphome/build/muse-luxe/.pioenvs/muse-luxe/firmware.elf}"
OUTPUT_DIR="${OUTPUT_DIR:-release}"
TOOLCHAIN="/config/.esphome/platformio/packages/toolchain-xtensa-esp-elf/bin"

if [[ ! -f "$ELF" ]]; then
  echo "Firmware ELF not found: $ELF" >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"

docker run --rm \
  -v "$PWD":/config \
  --entrypoint "$TOOLCHAIN/xtensa-esp-elf-size" \
  "$IMAGE" -A "/config/$ELF" > "$OUTPUT_DIR/firmware-sections.txt"

docker run --rm \
  -v "$PWD":/config \
  --entrypoint "$TOOLCHAIN/xtensa-esp-elf-nm" \
  "$IMAGE" --print-size --size-sort --radix=d "/config/$ELF" \
  | tail -n 120 > "$OUTPUT_DIR/firmware-largest-symbols.txt"

echo "Wrote section and largest-symbol reports to $OUTPUT_DIR/."
