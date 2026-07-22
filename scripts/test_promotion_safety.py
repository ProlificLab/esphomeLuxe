#!/usr/bin/env python3
"""Negative fixtures for atomic firmware promotion policy."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_promotion_safety.py"


def rejected(promotion: str, packager: str) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        promotion_path = directory / "promote.sh"
        packager_path = directory / "package.sh"
        promotion_path.write_text(promotion, encoding="utf-8")
        packager_path.write_text(packager, encoding="utf-8")
        result = subprocess.run(
            [
                "python3",
                str(CHECKER),
                "--promotion",
                str(promotion_path),
                "--packager",
                str(packager_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if result.returncode == 0:
            raise RuntimeError("Unsafe promotion fixture was accepted")


def main() -> None:
    promotion = (ROOT / "scripts/promote_firmware_channel.sh").read_text()
    packager = (ROOT / "scripts/package_firmware.sh").read_text()
    rejected(
        promotion.replace(
            '"$SCRIPT_DIR/verify_release.sh" "$manifest" "$artifact"',
            'echo "verification skipped"',
        ),
        packager,
    )
    rejected(
        promotion.replace(
            'python3 "$SCRIPT_DIR/check_qualification_record.py"',
            'python3 -c "print(1)"',
        ),
        packager,
    )
    rejected(
        promotion.replace("firmware-$version.ota.bin", "firmware.ota.bin"),
        packager,
    )
    rejected(
        promotion + '\nPVE_HOST="$PVE_HOST" "$SCRIPT_DIR/publish_ha_file.sh" "$artifact" "late.bin"\n',
        packager,
    )
    rejected(
        promotion.replace("Promotion requires a clean Git worktree", "Dirty tree accepted"),
        packager,
    )
    rejected(promotion.replace('clean "$config"', 'config "$config"'), packager)
    rejected(promotion.replace('compile "$config"', 'config "$config"'), packager)
    rejected(
        promotion,
        packager.replace('"source_commit": "$(git rev-parse HEAD)",\n', ""),
    )
    print("Promotion safety negative fixtures passed.")


if __name__ == "__main__":
    main()
