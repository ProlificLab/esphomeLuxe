#!/usr/bin/env python3
"""State-model tests for the two-satellite transient intercom contract."""

from __future__ import annotations

from dataclasses import dataclass, field
import unittest


ROOM_PLAYERS = {
    "bureau": "media_player.raspiaudio_muse_luxe",
    "cuisine": "media_player.muse_luxe_cuisine",
}
DEVICE_ROOMS = {"muse-luxe": "bureau", "muse-luxe-cuisine": "cuisine"}


@dataclass
class IntercomModel:
    enabled: bool = True
    status: str = "idle"
    caller: str = ""
    target: str = ""
    session: str = ""
    sequence: int = 0
    audible: list[str] = field(default_factory=list)
    delivered: list[tuple[str, str]] = field(default_factory=list)

    def call(self, source: str, target: str, available: set[str]) -> str:
        players = [ROOM_PLAYERS.get(source, ""), ROOM_PLAYERS.get(target, "")]
        if (
            not self.enabled
            or self.status in {"ringing", "connected"}
            or source == target
            or not all(players)
            or any(player not in available for player in players)
        ):
            raise ValueError("closed call guard")
        self.audible.append(f"ring:{target}")
        self.sequence += 1
        self.caller = source
        self.target = target
        self.session = f"session-{self.sequence}"
        self.status = "ringing"
        return self.session

    def accept(self, session: str) -> None:
        if self.status != "ringing" or session != self.session:
            raise ValueError("stale acceptance")
        self.audible.append("accepted")
        if self.status != "ringing" or session != self.session:
            raise ValueError("acceptance raced a close")
        self.status = "connected"

    def queue_relay(
        self,
        session: str,
        source: str,
        message: str,
        available: set[str],
    ) -> tuple[str, str, str]:
        destination = self.target if source == self.caller else self.caller if source == self.target else ""
        player = ROOM_PLAYERS.get(destination, "")
        if (
            self.status != "connected"
            or session != self.session
            or not destination
            or player not in available
            or not 1 <= len(message.strip()) <= 240
        ):
            raise ValueError("closed relay guard")
        return session, destination, message

    def deliver_relay(self, pending: tuple[str, str, str]) -> None:
        session, destination, message = pending
        if self.status != "connected" or session != self.session:
            raise ValueError("queued announcement guard expired")
        self.audible.append(f"relay:{destination}")
        self.delivered.append((destination, message))

    def relay(
        self,
        session: str,
        source: str,
        message: str,
        available: set[str],
    ) -> None:
        self.deliver_relay(self.queue_relay(session, source, message, available))

    def button(self, device: str, action: str) -> str:
        room = DEVICE_ROOMS.get(device, "")
        if room not in {self.caller, self.target} or not self.session:
            raise ValueError("untrusted intercom button")
        if action in {"accept", "decline"}:
            if self.status != "ringing" or room != self.target:
                raise ValueError("only target controls a ringing call")
        elif action == "hangup":
            if self.status not in {"ringing", "connected"}:
                raise ValueError("nothing to hang up")
        else:
            raise ValueError("unknown button action")
        return action

    def close(self, status: str = "ended") -> None:
        self.status = status

    def reset(self) -> None:
        if self.status in {"ringing", "connected"}:
            raise ValueError("active channel cannot be reset")
        self.status = "idle"
        self.caller = ""
        self.target = ""
        self.session = ""


class IntercomModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.available = set(ROOM_PLAYERS.values())

    def test_calls_work_in_both_explicit_directions(self) -> None:
        model = IntercomModel()
        first = model.call("bureau", "cuisine", self.available)
        self.assertEqual(model.status, "ringing")
        model.close()
        model.reset()
        second = model.call("cuisine", "bureau", self.available)
        self.assertNotEqual(first, second)
        self.assertEqual(model.audible, ["ring:cuisine", "ring:bureau"])

    def test_unavailable_player_is_rejected_without_mutation(self) -> None:
        model = IntercomModel()
        with self.assertRaises(ValueError):
            model.call("bureau", "cuisine", {ROOM_PLAYERS["bureau"]})
        self.assertEqual((model.status, model.session, model.audible), ("idle", "", []))

    def test_queued_old_relay_cannot_enter_a_new_session(self) -> None:
        model = IntercomModel()
        old_session = model.call("bureau", "cuisine", self.available)
        model.accept(old_session)
        pending = model.queue_relay(
            old_session,
            "bureau",
            "ancien message",
            self.available,
        )
        model.close()
        model.reset()
        new_session = model.call("cuisine", "bureau", self.available)
        model.accept(new_session)
        with self.assertRaises(ValueError):
            model.deliver_relay(pending)
        self.assertEqual(model.delivered, [])
        model.relay(new_session, "cuisine", "nouveau message", self.available)
        self.assertEqual(model.delivered, [("bureau", "nouveau message")])

    def test_stale_acceptance_and_unavailable_relay_are_rejected(self) -> None:
        model = IntercomModel()
        session = model.call("bureau", "cuisine", self.available)
        with self.assertRaises(ValueError):
            model.accept("old-session")
        model.accept(session)
        with self.assertRaises(ValueError):
            model.relay(session, "bureau", "bonjour", {ROOM_PLAYERS["bureau"]})
        self.assertEqual(model.delivered, [])

    def test_buttons_are_device_and_participant_bound(self) -> None:
        model = IntercomModel()
        session = model.call("bureau", "cuisine", self.available)
        with self.assertRaises(ValueError):
            model.button("muse-luxe", "accept")
        with self.assertRaises(ValueError):
            model.button("unknown-device", "decline")
        self.assertEqual(model.button("muse-luxe-cuisine", "accept"), "accept")
        model.accept(session)
        self.assertEqual(model.button("muse-luxe", "hangup"), "hangup")

    def test_restart_timeout_and_reset_leave_no_channel(self) -> None:
        for terminal in ("timed_out", "error"):
            with self.subTest(terminal=terminal):
                model = IntercomModel()
                model.call("bureau", "cuisine", self.available)
                model.close(terminal)
                model.reset()
                self.assertEqual((model.status, model.caller, model.target, model.session), ("idle", "", "", ""))

    def test_transcripts_are_bounded_and_never_stored_as_state(self) -> None:
        model = IntercomModel()
        session = model.call("bureau", "cuisine", self.available)
        model.accept(session)
        for message in ("", "x" * 241):
            with self.subTest(length=len(message)), self.assertRaises(ValueError):
                model.relay(session, "bureau", message, self.available)
        self.assertFalse(hasattr(model, "transcript"))


if __name__ == "__main__":
    unittest.main()
