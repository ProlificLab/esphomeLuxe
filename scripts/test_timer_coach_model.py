#!/usr/bin/env python3
"""Model-test timer checkpoint and non-urgent queue decisions."""

from __future__ import annotations

import unittest


CHECKPOINTS = {300, 60, 30, 10}
BUSY_VOICE_STATES = {"starting", "listening", "answering"}


def should_announce(
    *, enabled: bool, active: int, name: str, old: int, remaining: int
) -> bool:
    return (
        enabled
        and active > 0
        and name not in {"", "none", "unknown", "unavailable"}
        and remaining in CHECKPOINTS
        and old > remaining
        and old - remaining <= 5
    )


def announcement_ready(
    *, player: str, player_state: str, continuous: bool, voice_state: str
) -> bool:
    muse_busy = player == "media_player.raspiaudio_muse_luxe" and (
        continuous or voice_state in BUSY_VOICE_STATES
    )
    return player_state not in {"playing", "buffering"} and not muse_busy


class TimerCoachContractTest(unittest.TestCase):
    def test_normal_ticks_cross_only_four_checkpoints(self) -> None:
        observed = [
            second
            for second in range(360, -1, -1)
            if should_announce(
                enabled=True,
                active=2,
                name="pates",
                old=second + 1,
                remaining=second,
            )
        ]
        self.assertEqual(observed, [300, 60, 30, 10])

    def test_disabled_invalid_and_finished_timers_are_silent(self) -> None:
        self.assertFalse(should_announce(enabled=False, active=1, name="four", old=61, remaining=60))
        self.assertFalse(should_announce(enabled=True, active=0, name="four", old=61, remaining=60))
        self.assertFalse(should_announce(enabled=True, active=1, name="none", old=61, remaining=60))

    def test_reconnect_and_duration_jump_are_not_replayed(self) -> None:
        self.assertFalse(should_announce(enabled=True, active=1, name="four", old=-1, remaining=60))
        self.assertFalse(should_announce(enabled=True, active=1, name="four", old=300, remaining=60))
        self.assertFalse(should_announce(enabled=True, active=1, name="four", old=30, remaining=60))

    def test_near_tick_jitter_is_tolerated(self) -> None:
        self.assertTrue(should_announce(enabled=True, active=1, name="four", old=62, remaining=60))
        self.assertTrue(should_announce(enabled=True, active=1, name="four", old=35, remaining=30))
        self.assertFalse(should_announce(enabled=True, active=1, name="four", old=36, remaining=30))

    def test_nonurgent_audio_waits_for_music_and_conversation(self) -> None:
        self.assertFalse(announcement_ready(player="media_player.raspiaudio_muse_luxe", player_state="playing", continuous=False, voice_state="waiting"))
        self.assertFalse(announcement_ready(player="media_player.raspiaudio_muse_luxe", player_state="idle", continuous=True, voice_state="waiting"))
        self.assertFalse(announcement_ready(player="media_player.raspiaudio_muse_luxe", player_state="idle", continuous=False, voice_state="listening"))
        self.assertTrue(announcement_ready(player="media_player.raspiaudio_muse_luxe", player_state="idle", continuous=False, voice_state="waiting"))
        self.assertTrue(announcement_ready(player="media_player.kitchen", player_state="idle", continuous=True, voice_state="listening"))


if __name__ == "__main__":
    unittest.main()
