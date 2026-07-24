#!/usr/bin/env python3
"""Model-check temporary Music Assistant group lifecycle decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
import unittest


PREFIX = "media_player.raspiaudio_muse_luxe"


@dataclass
class GroupModel:
    state: str = "idle"
    master: str = ""
    members: list[str] = field(default_factory=list)
    timer_active: bool = False
    claimed_at: int = 0
    volumes: dict[str, float] = field(default_factory=dict)
    unjoined: list[str] = field(default_factory=list)

    def create(
        self,
        master: str,
        members: list[str],
        duration: int,
        available: set[str],
        volumes: dict[str, float],
        enabled: bool = True,
        fail_join: bool = False,
    ) -> None:
        requested = [master, *members]
        players = list(dict.fromkeys(requested))
        if not enabled:
            raise PermissionError("opt-in disabled")
        if self.state != "idle":
            raise RuntimeError("group already claimed")
        if (
            len(players) != len(requested)
            or not 2 <= len(players) <= 4
            or not 5 <= duration <= 240
            or any(player not in available or not player.startswith(PREFIX) for player in players)
        ):
            raise ValueError("invalid group")
        self.master = master
        self.members = members.copy()
        self.claimed_at = 100
        self.state = "grouping"
        if fail_join:
            return
        self.volumes = {player: volumes[player] for player in players}
        self.state = "active"
        self.timer_active = True

    def close(self, fail_after: int | None = None) -> None:
        if self.state != "active":
            self.state = "review"
            raise RuntimeError("invalid close")
        self.state = "closing"
        self.timer_active = False
        for index, player in enumerate([*self.members, self.master]):
            if fail_after is not None and index == fail_after:
                return
            self.unjoined.append(player)
        self.clear()

    def restart(self) -> None:
        if self.state in {"grouping", "closing"} or (
            self.state == "active" and not self.timer_active
        ):
            self.state = "review"

    def watchdog(self, now: int) -> None:
        if self.state in {"grouping", "closing"} and now - self.claimed_at >= 120:
            self.state = "review"

    def recover(self, confirmed: bool, available: set[str]) -> None:
        players = list(dict.fromkeys([*self.members, self.master]))
        if (
            not confirmed
            or self.state not in {"grouping", "closing", "review"}
            or not 2 <= len(players) <= 4
            or any(player not in available or not player.startswith(PREFIX) for player in players)
        ):
            raise PermissionError("explicit valid recovery required")
        self.state = "closing"
        self.unjoined.extend(players)
        self.clear()

    def clear(self) -> None:
        self.state = "idle"
        self.master = ""
        self.members = []
        self.timer_active = False
        self.claimed_at = 0


class GroupContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.master = f"{PREFIX}_2"
        self.member = f"{PREFIX}_kitchen"
        self.available = {self.master, self.member}
        self.volumes = {self.master: 0.35, self.member: 0.55}

    def test_group_is_bounded_and_preserves_relative_volumes(self) -> None:
        group = GroupModel()
        group.create(self.master, [self.member], 120, self.available, self.volumes)
        self.assertEqual(group.state, "active")
        self.assertEqual(group.volumes, self.volumes)
        self.assertAlmostEqual(group.volumes[self.member] - group.volumes[self.master], 0.20)
        group.close()
        self.assertEqual(group.state, "idle")
        self.assertEqual(group.unjoined, [self.member, self.master])

    def test_disabled_duplicate_foreign_and_long_groups_are_rejected(self) -> None:
        with self.assertRaises(PermissionError):
            GroupModel().create(self.master, [self.member], 120, self.available, self.volumes, enabled=False)
        with self.assertRaises(ValueError):
            GroupModel().create(self.master, [self.master], 120, self.available, self.volumes)
        with self.assertRaises(ValueError):
            GroupModel().create(self.master, ["media_player.television"], 120, self.available, self.volumes)
        with self.assertRaises(ValueError):
            GroupModel().create(self.master, [self.member], 241, self.available, self.volumes)

    def test_join_crash_is_quarantined_without_automatic_unjoin(self) -> None:
        group = GroupModel()
        group.create(self.master, [self.member], 120, self.available, self.volumes, fail_join=True)
        group.restart()
        self.assertEqual(group.state, "review")
        self.assertEqual(group.unjoined, [])
        with self.assertRaises(PermissionError):
            group.recover(False, self.available)
        group.recover(True, self.available)
        self.assertEqual(group.state, "idle")
        self.assertEqual(group.unjoined, [self.member, self.master])

    def test_close_failure_is_quarantined_and_never_cleared(self) -> None:
        group = GroupModel()
        group.create(self.master, [self.member], 120, self.available, self.volumes)
        group.close(fail_after=1)
        self.assertEqual(group.state, "closing")
        self.assertEqual(group.master, self.master)
        group.watchdog(219)
        self.assertEqual(group.state, "closing")
        group.watchdog(220)
        self.assertEqual(group.state, "review")

    def test_active_group_survives_restart_only_with_restored_timer(self) -> None:
        group = GroupModel()
        group.create(self.master, [self.member], 120, self.available, self.volumes)
        group.restart()
        self.assertEqual(group.state, "active")
        group.timer_active = False
        group.restart()
        self.assertEqual(group.state, "review")


if __name__ == "__main__":
    unittest.main()
