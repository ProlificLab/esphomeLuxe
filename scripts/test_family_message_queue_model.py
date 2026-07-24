#!/usr/bin/env python3
"""Model-check the bounded family-message state transitions."""

from __future__ import annotations

from dataclasses import dataclass
import unittest


@dataclass
class Slot:
    state: str = "empty"
    recipient: str = ""
    text: str = ""
    expiry: int = 0
    claimed_at: int = 0
    order: int = 0


class QueueModel:
    def __init__(self) -> None:
        self.slots = [Slot(), Slot(), Slot()]
        self.delivered: list[str] = []
        self.expired: list[str] = []
        self.sequence = 0

    def queue(self, recipient: str, text: str, expiry: int, home: set[str]) -> str:
        if not 1 <= len(text) <= 240:
            raise ValueError("bounded transcript")
        if recipient in home:
            self.delivered.append(text)
            return "immediate"
        for number, slot in enumerate(self.slots, 1):
            if slot.state == "empty":
                slot.state = "pending"
                slot.recipient = recipient
                slot.text = text
                slot.expiry = expiry
                self.sequence += 1
                slot.order = self.sequence
                return f"slot-{number}"
        raise OverflowError("queue full")

    def process(self, now: int, home: set[str], startup: bool = False) -> None:
        for slot in self.slots:
            if slot.state == "delivering" and (
                startup or now - slot.claimed_at >= 360
            ):
                slot.state = "review"
        for slot in sorted(self.slots, key=lambda item: item.order):
            if slot.state != "pending":
                continue
            if now >= slot.expiry:
                self.expired.append(slot.text)
                self.clear(slot)
            elif slot.recipient in home:
                slot.state = "delivering"
                slot.claimed_at = now
                self.delivered.append(slot.text)
                self.clear(slot)

    def retry(self, number: int, now: int) -> None:
        slot = self.slots[number - 1]
        if slot.state != "review":
            raise ValueError("only uncertain messages need explicit retry")
        slot.state = "delivering"
        slot.claimed_at = now
        self.delivered.append(slot.text)
        self.clear(slot)

    @staticmethod
    def clear(slot: Slot) -> None:
        slot.state = "empty"
        slot.recipient = ""
        slot.text = ""
        slot.expiry = 0
        slot.claimed_at = 0
        slot.order = 0


class QueueContractTest(unittest.TestCase):
    def test_three_slots_and_fifo_delivery(self) -> None:
        queue = QueueModel()
        for text in ("one", "two", "three"):
            queue.queue("person.anna", text, 1000, set())
        with self.assertRaises(OverflowError):
            queue.queue("person.anna", "four", 1000, set())
        queue.process(10, {"person.anna"})
        self.assertEqual(queue.delivered, ["one", "two", "three"])
        self.assertTrue(all(slot.state == "empty" for slot in queue.slots))

    def test_immediate_does_not_consume_slot(self) -> None:
        queue = QueueModel()
        self.assertEqual(
            queue.queue("person.anna", "home", 1000, {"person.anna"}),
            "immediate",
        )
        self.assertEqual(queue.delivered, ["home"])
        self.assertTrue(all(slot.state == "empty" for slot in queue.slots))

    def test_reused_low_slot_does_not_jump_fifo(self) -> None:
        queue = QueueModel()
        queue.queue("person.other", "cleared", 1000, set())
        queue.queue("person.anna", "older", 1000, set())
        queue.clear(queue.slots[0])
        queue.queue("person.anna", "newer", 1000, set())
        queue.process(10, {"person.anna"})
        self.assertEqual(queue.delivered, ["older", "newer"])

    def test_expiry_never_delivers(self) -> None:
        queue = QueueModel()
        queue.queue("person.anna", "expired", 50, set())
        queue.process(50, {"person.anna"})
        self.assertEqual(queue.delivered, [])
        self.assertEqual(queue.expired, ["expired"])

    def test_restart_quarantines_uncertain_delivery(self) -> None:
        queue = QueueModel()
        queue.queue("person.anna", "uncertain", 1000, set())
        slot = queue.slots[0]
        slot.state = "delivering"
        slot.claimed_at = 20
        queue.process(21, {"person.anna"}, startup=True)
        self.assertEqual(slot.state, "review")
        self.assertEqual(queue.delivered, [])
        queue.process(500, {"person.anna"})
        self.assertEqual(queue.delivered, [])
        queue.retry(1, 501)
        self.assertEqual(queue.delivered, ["uncertain"])

    def test_stale_claim_is_quarantined_without_replay(self) -> None:
        queue = QueueModel()
        queue.queue("person.anna", "stale", 2000, set())
        slot = queue.slots[0]
        slot.state = "delivering"
        slot.claimed_at = 10
        queue.process(369, {"person.anna"})
        self.assertEqual(slot.state, "delivering")
        queue.process(370, {"person.anna"})
        self.assertEqual(slot.state, "review")
        self.assertEqual(queue.delivered, [])

    def test_transcript_bounds(self) -> None:
        queue = QueueModel()
        with self.assertRaises(ValueError):
            queue.queue("person.anna", "", 1000, set())
        with self.assertRaises(ValueError):
            queue.queue("person.anna", "x" * 241, 1000, set())


if __name__ == "__main__":
    unittest.main()
