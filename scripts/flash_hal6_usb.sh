#!/usr/bin/env bash
set -euo pipefail

usage="Usage: flash_hal6_usb.sh HAL6_OTA HAL6_FACTORY SERIAL_PORT"
OTA="${1:?$usage}"
FACTORY="${2:?$usage}"
SERIAL_PORT="${3:?$usage}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
FACTORY_SHA256="16ad19ae504dae9e75d6be0cb72b6ada34bf932fae0f972a89b5230dc20c01ac"

validate_serial() {
  case "$SERIAL_PORT" in
    /dev/cu.*|/dev/tty.*) ;;
    *)
      echo "Serial port must be an explicit /dev/cu.* or /dev/tty.* device." >&2
      exit 1
      ;;
  esac
  if [[ -L "$SERIAL_PORT" || ! -c "$SERIAL_PORT" ]]; then
    echo "Serial port must be a local non-symlink character device." >&2
    exit 1
  fi
}

validate() {
  python3 "$SCRIPT_DIR/check_hal6_recovery_manifest.py" >/dev/null
  python3 "$SCRIPT_DIR/check_hal6_usb_recovery.py" \
    "$OTA" "$FACTORY" --manifest "$ROOT/manifest_update.json" >/dev/null
}

validate_serial
validate
confirmation="FLASH HAL6 USB $FACTORY_SHA256 $SERIAL_PORT"
if [[ -z "${HAL6_USB_FLASH_CONFIRM:-}" && -t 0 ]]; then
  printf 'This erases active configuration in the written flash range.\n' >&2
  printf 'Type exactly: %s\n> ' "$confirmation" >&2
  IFS= read -r HAL6_USB_FLASH_CONFIRM
fi
if [[ "${HAL6_USB_FLASH_CONFIRM:-}" != "$confirmation" ]]; then
  echo "USB flash confirmation is missing or does not match." >&2
  exit 1
fi

# Close the confirmation race before opening the serial device.
validate
validate_serial
factory_abs="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$FACTORY")"
uv run --with esptool==5.3.1 esptool \
  --chip esp32 \
  --port "$SERIAL_PORT" \
  --baud 460800 \
  write-flash 0x0 "$factory_abs"

echo "Canonical hal.6 USB image written and verified by esptool."
echo "Reprovision Wi-Fi, then restore the encrypted Home Assistant API entry."
