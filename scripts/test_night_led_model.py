#!/usr/bin/env python3
"""Model-test bounded brightness decisions for every firmware phase."""

from __future__ import annotations

import unittest


DAY = {
    "starting": 40,
    "waiting": 100,
    "playing": 60,
    "listening": 100,
    "answering": 100,
    "offline": 45,
    "error": 100,
    "privacy": 35,
    "rescue": 80,
}
NIGHT = {
    "starting": 15,
    "waiting": 10,
    "playing": 10,
    "listening": 25,
    "answering": 20,
    "offline": 15,
    "error": 35,
    "privacy": 20,
    "rescue": 35,
}


def brightness(phase: str, night: bool, active_timers: int = 0) -> int:
    if active_timers > 0 and phase == "waiting":
        return 15 if night else 40
    return (NIGHT if night else DAY).get(phase, 15 if night else 40)


class NightLedContractTest(unittest.TestCase):
    def test_every_night_phase_is_dimmer_but_visible(self) -> None:
        for phase in DAY:
            with self.subTest(phase=phase):
                self.assertGreater(brightness(phase, True), 0)
                self.assertLess(brightness(phase, True), brightness(phase, False))

    def test_microphone_and_safety_states_keep_visibility_floors(self) -> None:
        self.assertGreaterEqual(brightness("listening", True), 25)
        self.assertGreaterEqual(brightness("privacy", True), 20)
        self.assertGreaterEqual(brightness("error", True), 35)
        self.assertGreaterEqual(brightness("rescue", True), 35)

    def test_active_timer_has_a_separate_day_and_night_level(self) -> None:
        self.assertEqual(brightness("waiting", False, 2), 40)
        self.assertEqual(brightness("waiting", True, 2), 15)

    def test_timer_override_never_hides_nonwaiting_safety_phase(self) -> None:
        self.assertEqual(brightness("privacy", True, 1), NIGHT["privacy"])
        self.assertEqual(brightness("error", False, 1), DAY["error"])

    def test_unknown_phase_uses_bounded_fallback(self) -> None:
        self.assertEqual(brightness("unknown", False), 40)
        self.assertEqual(brightness("unknown", True), 15)


if __name__ == "__main__":
    unittest.main()
