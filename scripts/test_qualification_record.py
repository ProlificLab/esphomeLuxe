#!/usr/bin/env python3
"""Unit and negative tests for release qualification records."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import check_qualification_record as checker
from test_acoustic_guardian_evidence import valid_evidence as valid_acoustic_evidence
from test_family_message_evidence import valid_evidence as valid_family_message_evidence
from test_hal9_modes_evidence import valid_evidence as valid_modes_evidence
from test_interpreter_evidence import valid_evidence as valid_interpreter_evidence
from test_night_led_evidence import valid_evidence as valid_night_led_evidence
from test_offline_rescue_evidence import valid_evidence as valid_rescue_evidence
from test_physical_controls_evidence import valid_evidence as valid_physical_evidence
from test_timer_evidence import valid_evidence as valid_timer_evidence
from test_video_review_evidence import valid_evidence as valid_video_evidence
from test_endurance_summary import valid_summary
from monitor_endurance import write_summary


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_qualification_record.py"
TEMPLATE = ROOT / "docs/qualification-record.example.json"
COMMIT = "a" * 40


def gate() -> dict[str, object]:
    return {"passed": True, "evidence": "CI run 123456 and reviewed log"}


class QualificationRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.artifact = self.directory / "muse-luxe-2026.1.0-hal.10.ota.bin"
        self.artifact.write_bytes(b"qualified firmware fixture")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def record(self, channel: str, version: str) -> dict[str, object]:
        required = checker.STABLE_GATES if channel == "stable" else checker.BETA_GATES
        return {
            "schema_version": 1,
            "channel": channel,
            "version": version,
            "source_commit": COMMIT,
            "firmware_sha256": self.digest,
            "reviewer": "Household release reviewer",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "canary_device": "muse-luxe-canary-bureau",
            "compatibility": {
                "hardware": "Raspiaudio Muse Luxe ESP32",
                "home_assistant": "2026.7.2",
                "esphome": "2025.10.5",
                "esp_idf": "5.4.2",
            },
            "feature_scope": ["voice satellite", "local recovery"],
            "open_gates": [] if channel == "stable" else ["stable gates remain"],
            "gates": {name: gate() for name in required},
        }

    def run_check(
        self,
        record: dict[str, object],
        channel: str,
        version: str,
        tamper_endurance: bool = False,
        tamper_modes: bool = False,
        tamper_physical_controls: bool = False,
        unbound_physical_controls: bool = False,
        tamper_night_led: bool = False,
        unbound_night_led: bool = False,
        tamper_timer: bool = False,
        unbound_timer: bool = False,
        tamper_offline_rescue: bool = False,
        unbound_offline_rescue: bool = False,
        split_offline_rescue_gates: bool = False,
        tamper_interpreter: bool = False,
        unbound_interpreter: bool = False,
        tamper_acoustic: bool = False,
        unbound_acoustic: bool = False,
        tamper_video: bool = False,
        unbound_video: bool = False,
        tamper_family_message: bool = False,
        unbound_family_message: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        record_path = self.directory / "qualification.json"
        manifest_path = self.directory / "manifest.json"
        modes_path = self.directory / "modes.json"
        modes = valid_modes_evidence()
        modes["device"]["project_version"] = version
        modes_path.write_text(json.dumps(modes), encoding="utf-8")
        modes_hash = hashlib.sha256(modes_path.read_bytes()).hexdigest()
        record["gates"]["mode_api_transitions"]["evidence"] = (
            f"sha256:{modes_hash} {modes_path.name}"
        )
        if tamper_modes:
            modes_path.write_text("{}\n", encoding="utf-8")
        physical_path = self.directory / "physical-controls.json"
        physical = valid_physical_evidence(version, self.digest)
        physical_path.write_text(json.dumps(physical), encoding="utf-8")
        physical_hash = hashlib.sha256(physical_path.read_bytes()).hexdigest()
        record["gates"]["physical_controls"]["evidence"] = (
            "physical-controls.json"
            if unbound_physical_controls
            else f"sha256:{physical_hash} {physical_path.name}"
        )
        if tamper_physical_controls:
            physical_path.write_text("{}\n", encoding="utf-8")
        if channel == "stable":
            package_path = ROOT / "home-assistant/packages/muse_luxe.yaml"
            package_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
            night_led_path = self.directory / "night-led.json"
            night_led = valid_night_led_evidence(
                version,
                self.digest,
                package_hash,
            )
            night_led_path.write_text(json.dumps(night_led), encoding="utf-8")
            night_led_hash = hashlib.sha256(night_led_path.read_bytes()).hexdigest()
            record["gates"]["night_led_profiles"]["evidence"] = (
                "night-led.json"
                if unbound_night_led
                else f"sha256:{night_led_hash} {night_led_path.name}"
            )
            if tamper_night_led:
                night_led_path.write_text("{}\n", encoding="utf-8")
            if "timer_multi_pause_reconnect" in record["gates"]:
                timer_package_path = (
                    ROOT / "home-assistant/packages/muse_timer_coach.yaml"
                )
                timer_package_hash = hashlib.sha256(
                    timer_package_path.read_bytes()
                ).hexdigest()
                timer_path = self.directory / "timer.json"
                timer = valid_timer_evidence(
                    version,
                    self.digest,
                    package_hash,
                    timer_package_hash,
                )
                timer_path.write_text(json.dumps(timer), encoding="utf-8")
                timer_hash = hashlib.sha256(timer_path.read_bytes()).hexdigest()
                record["gates"]["timer_multi_pause_reconnect"]["evidence"] = (
                    "timer.json"
                    if unbound_timer
                    else f"sha256:{timer_hash} {timer_path.name}"
                )
                if tamper_timer:
                    timer_path.write_text("{}\n", encoding="utf-8")
            if {
                "emergency_offline",
                "offline_rescue_physical",
            } <= set(record["gates"]):
                rescue_package = ROOT / "packages/offline_rescue.yaml"
                rescue_component = (
                    ROOT / "components/offline_media/offline_media.cpp"
                )
                rescue_path = self.directory / "offline-rescue.json"
                rescue = valid_rescue_evidence(
                    version,
                    self.digest,
                    hashlib.sha256(rescue_package.read_bytes()).hexdigest(),
                    hashlib.sha256(rescue_component.read_bytes()).hexdigest(),
                )
                rescue_path.write_text(json.dumps(rescue), encoding="utf-8")
                rescue_hash = hashlib.sha256(rescue_path.read_bytes()).hexdigest()
                bound_rescue = (
                    "offline-rescue.json"
                    if unbound_offline_rescue
                    else f"sha256:{rescue_hash} {rescue_path.name}"
                )
                record["gates"]["offline_rescue_physical"]["evidence"] = (
                    bound_rescue
                )
                record["gates"]["emergency_offline"]["evidence"] = bound_rescue
                if split_offline_rescue_gates:
                    duplicate_path = self.directory / "emergency-offline.json"
                    duplicate_path.write_bytes(rescue_path.read_bytes())
                    record["gates"]["emergency_offline"]["evidence"] = (
                        f"sha256:{rescue_hash} {duplicate_path.name}"
                    )
                if tamper_offline_rescue:
                    rescue_path.write_text("{}\n", encoding="utf-8")
            interpreter_package = (
                ROOT / "home-assistant/packages/muse_interpreter.yaml"
            )
            interpreter_config = ROOT / "scripts/configure_interpreter.py"
            interpreter_sentences = (
                ROOT
                / "home-assistant/custom_sentences/fr/muse_interpreter.yaml"
            )
            interpreter_path = self.directory / "interpreter.json"
            interpreter = valid_interpreter_evidence(
                version,
                self.digest,
                hashlib.sha256(interpreter_package.read_bytes()).hexdigest(),
                hashlib.sha256(interpreter_config.read_bytes()).hexdigest(),
                hashlib.sha256(interpreter_sentences.read_bytes()).hexdigest(),
            )
            interpreter_path.write_text(json.dumps(interpreter), encoding="utf-8")
            interpreter_hash = hashlib.sha256(
                interpreter_path.read_bytes()
            ).hexdigest()
            record["gates"]["interpreter_bilingual"]["evidence"] = (
                "interpreter.json"
                if unbound_interpreter
                else f"sha256:{interpreter_hash} {interpreter_path.name}"
            )
            if tamper_interpreter:
                interpreter_path.write_text("{}\n", encoding="utf-8")
            acoustic_package = (
                ROOT / "home-assistant/packages/muse_acoustic_guardian.yaml"
            )
            acoustic_preparer = (
                ROOT / "scripts/prepare_frigate_acoustic_guardian.py"
            )
            acoustic_policy = (
                ROOT / "frigate/acoustic-guardian-policy.example.yaml"
            )
            acoustic_path = self.directory / "acoustic.json"
            acoustic = valid_acoustic_evidence(
                version,
                self.digest,
                hashlib.sha256(acoustic_package.read_bytes()).hexdigest(),
                hashlib.sha256(acoustic_preparer.read_bytes()).hexdigest(),
                hashlib.sha256(acoustic_policy.read_bytes()).hexdigest(),
            )
            acoustic_path.write_text(json.dumps(acoustic), encoding="utf-8")
            acoustic_hash = hashlib.sha256(acoustic_path.read_bytes()).hexdigest()
            record["gates"]["acoustic_guardian_physical"]["evidence"] = (
                "acoustic.json"
                if unbound_acoustic
                else f"sha256:{acoustic_hash} {acoustic_path.name}"
            )
            if tamper_acoustic:
                acoustic_path.write_text("{}\n", encoding="utf-8")
            video_package = ROOT / "home-assistant/packages/muse_video_review.yaml"
            video_dashboard = (
                ROOT / "home-assistant/dashboards/muse-video-review.yaml"
            )
            video_provisioner = (
                ROOT / "scripts/provision_video_review_dashboard.sh"
            )
            video_path = self.directory / "video-review.json"
            video = valid_video_evidence(
                version,
                self.digest,
                hashlib.sha256(video_package.read_bytes()).hexdigest(),
                hashlib.sha256(video_dashboard.read_bytes()).hexdigest(),
                hashlib.sha256(video_provisioner.read_bytes()).hexdigest(),
            )
            video_path.write_text(json.dumps(video), encoding="utf-8")
            video_hash = hashlib.sha256(video_path.read_bytes()).hexdigest()
            record["gates"]["video_review_authenticated"]["evidence"] = (
                "video-review.json"
                if unbound_video
                else f"sha256:{video_hash} {video_path.name}"
            )
            if tamper_video:
                video_path.write_text("{}\n", encoding="utf-8")
            family_package = (
                ROOT / "home-assistant/packages/muse_family_messages.yaml"
            )
            family_base = ROOT / "home-assistant/packages/muse_luxe.yaml"
            family_provisioner = ROOT / "scripts/provision_family_messages.sh"
            family_path = self.directory / "family-message.json"
            family = valid_family_message_evidence(
                version,
                self.digest,
                hashlib.sha256(family_package.read_bytes()).hexdigest(),
                hashlib.sha256(family_base.read_bytes()).hexdigest(),
                hashlib.sha256(family_provisioner.read_bytes()).hexdigest(),
            )
            family_path.write_text(json.dumps(family), encoding="utf-8")
            family_hash = hashlib.sha256(family_path.read_bytes()).hexdigest()
            record["gates"]["family_message_delivery"]["evidence"] = (
                "family-message.json"
                if unbound_family_message
                else f"sha256:{family_hash} {family_path.name}"
            )
            if tamper_family_message:
                family_path.write_text("{}\n", encoding="utf-8")
            summary_path = self.directory / "endurance.summary.json"
            summary = valid_summary()
            summary["device"]["project_version"] = version
            write_summary(summary_path, summary)
            summary_hash = hashlib.sha256(summary_path.read_bytes()).hexdigest()
            record["gates"]["idle_endurance_24h"]["evidence"] = (
                f"sha256:{summary_hash} {summary_path.name}"
            )
            if tamper_endurance:
                summary_path.write_text("{}\n", encoding="utf-8")
        record_path.write_text(json.dumps(record), encoding="utf-8")
        manifest_path.write_text(
            json.dumps({"version": version, "channel": channel}),
            encoding="utf-8",
        )
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--record",
                str(record_path),
                "--manifest",
                str(manifest_path),
                "--artifact",
                str(self.artifact),
                "--channel",
                channel,
                "--source-commit",
                COMMIT,
            ],
            capture_output=True,
            check=False,
            text=True,
        )

    def test_beta_record_passes(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        result = self.run_check(self.record("beta", version), "beta", version)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stable_record_passes(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(self.record("stable", version), "stable", version)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_template_and_checker_cover_every_roadmap_gate(self) -> None:
        template_gates = set(json.loads(TEMPLATE.read_text(encoding="utf-8"))["gates"])
        self.assertEqual(template_gates, checker.STABLE_GATES)
        self.assertTrue(checker.ROADMAP_FEATURE_GATES <= checker.STABLE_GATES)
        self.assertTrue(checker.ROADMAP_FEATURE_GATES.isdisjoint(checker.BETA_GATES))

    def test_missing_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["gates"].pop("tts_cycles_100")
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_stable_missing_timer_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        record["gates"].pop("timer_multi_pause_reconnect")
        self.assertNotEqual(self.run_check(record, "stable", version).returncode, 0)

    def test_false_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["gates"]["canary_ota"]["passed"] = False
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_hash_mismatch_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["firmware_sha256"] = "0" * 64
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_commit_mismatch_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["source_commit"] = "b" * 40
        self.assertNotEqual(self.run_check(record, "beta", version).returncode, 0)

    def test_stable_prerelease_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-rc.1"
        record = self.record("stable", version)
        self.assertNotEqual(self.run_check(record, "stable", version).returncode, 0)

    def test_stable_open_gate_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        record["open_gates"] = ["physical gate remains"]
        self.assertNotEqual(self.run_check(record, "stable", version).returncode, 0)

    def test_stable_unbound_endurance_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        record["gates"]["idle_endurance_24h"]["evidence"] = "missing.json"
        # Write the record directly so run_check cannot replace this fixture.
        record_path = self.directory / "qualification.json"
        manifest_path = self.directory / "manifest.json"
        record_path.write_text(json.dumps(record), encoding="utf-8")
        manifest_path.write_text(
            json.dumps({"version": version, "channel": "stable"}), encoding="utf-8"
        )
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--record",
                str(record_path),
                "--manifest",
                str(manifest_path),
                "--artifact",
                str(self.artifact),
                "--channel",
                "stable",
                "--source-commit",
                COMMIT,
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_stable_tampered_endurance_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        result = self.run_check(
            record, "stable", version, tamper_endurance=True
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_modes_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        result = self.run_check(record, "beta", version, tamper_modes=True)
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_modes_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        record["gates"]["mode_api_transitions"]["evidence"] = "modes.json"
        record_path = self.directory / "qualification.json"
        manifest_path = self.directory / "manifest.json"
        record_path.write_text(json.dumps(record), encoding="utf-8")
        manifest_path.write_text(
            json.dumps({"version": version, "channel": "beta"}), encoding="utf-8"
        )
        result = subprocess.run(
            [
                "python3", str(SCRIPT), "--record", str(record_path),
                "--manifest", str(manifest_path), "--artifact", str(self.artifact),
                "--channel", "beta", "--source-commit", COMMIT,
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_physical_controls_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        result = self.run_check(
            record,
            "beta",
            version,
            tamper_physical_controls=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_physical_controls_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10-beta.1"
        record = self.record("beta", version)
        result = self.run_check(
            record,
            "beta",
            version,
            unbound_physical_controls=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_night_led_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        result = self.run_check(
            record,
            "stable",
            version,
            tamper_night_led=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_night_led_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        result = self.run_check(
            record,
            "stable",
            version,
            unbound_night_led=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_timer_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        result = self.run_check(
            record,
            "stable",
            version,
            tamper_timer=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_timer_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        record = self.record("stable", version)
        result = self.run_check(
            record,
            "stable",
            version,
            unbound_timer=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_offline_rescue_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            tamper_offline_rescue=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_offline_rescue_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            unbound_offline_rescue=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_split_offline_rescue_gate_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            split_offline_rescue_gates=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_interpreter_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            tamper_interpreter=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_interpreter_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            unbound_interpreter=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_acoustic_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            tamper_acoustic=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_acoustic_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            unbound_acoustic=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_video_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            tamper_video=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_video_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            unbound_video=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_tampered_family_message_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            tamper_family_message=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unbound_family_message_evidence_is_rejected(self) -> None:
        version = "2026.1.0-hal.10"
        result = self.run_check(
            self.record("stable", version),
            "stable",
            version,
            unbound_family_message=True,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
