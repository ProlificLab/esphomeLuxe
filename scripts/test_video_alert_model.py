#!/usr/bin/env python3
"""State-model tests for bounded Frigate person-event deduplication."""

from __future__ import annotations

from dataclasses import dataclass, field
import unittest


@dataclass
class AlertModel:
    enabled: bool = True
    night: bool = False
    minimum_confidence: float = 0.75
    cooldown_seconds: int = 60
    last_announcement: float = -60
    recent_ids: list[str] = field(default_factory=list)

    def process(
        self,
        now: float,
        event_id: str,
        camera: str = "sonnette",
        label: str = "person",
        confidence: float = 0.9,
        event_type: str = "new",
        event_start: float | None = None,
        false_positive: bool = False,
    ) -> bool:
        start = now if event_start is None else event_start
        age = now - start
        accepted = (
            self.enabled
            and not self.night
            and event_type in {"new", "update"}
            and 0 < len(event_id) <= 32
            and "|" not in event_id
            and label == "person"
            and not false_positive
            and confidence >= self.minimum_confidence
            and camera in {"sonnette", "avant_jardin"}
            and -5 <= age <= 30
            and event_id not in self.recent_ids
            and now - self.last_announcement >= self.cooldown_seconds
        )
        if not accepted:
            return False
        self.recent_ids = (self.recent_ids + [event_id])[-7:]
        self.last_announcement = now
        return True


class VideoAlertModelTests(unittest.TestCase):
    def test_same_event_never_repeats_after_other_event_or_cooldown(self) -> None:
        model = AlertModel()
        self.assertTrue(model.process(0, "event-a"))
        self.assertTrue(model.process(60, "event-b"))
        self.assertFalse(model.process(120, "event-a", event_type="update"))
        self.assertEqual(model.recent_ids, ["event-a", "event-b"])

    def test_global_cooldown_suppresses_burst_without_mutation(self) -> None:
        model = AlertModel()
        self.assertTrue(model.process(0, "event-a"))
        self.assertFalse(model.process(59, "event-b", camera="avant_jardin"))
        self.assertEqual(model.recent_ids, ["event-a"])
        self.assertEqual(model.last_announcement, 0)
        self.assertTrue(model.process(60, "event-b", camera="avant_jardin"))

    def test_history_is_fifo_and_bounded_to_seven(self) -> None:
        model = AlertModel()
        for index in range(9):
            self.assertTrue(model.process(index * 60, f"event-{index}"))
        self.assertEqual(
            model.recent_ids,
            [f"event-{index}" for index in range(2, 9)],
        )

    def test_stale_and_too_future_events_are_rejected(self) -> None:
        model = AlertModel()
        self.assertFalse(model.process(100, "stale", event_start=69))
        self.assertFalse(model.process(100, "future", event_start=106))
        self.assertTrue(model.process(100, "edge-old", event_start=70))

    def test_all_content_and_privacy_filters_are_closed(self) -> None:
        fixtures = (
            {"event_id": ""},
            {"event_id": "x" * 33},
            {"event_id": "bad|id"},
            {"event_id": "car", "label": "car"},
            {"event_id": "low", "confidence": 0.74},
            {"event_id": "false", "false_positive": True},
            {"event_id": "camera", "camera": "cuisine"},
            {"event_id": "end", "event_type": "end"},
        )
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertFalse(AlertModel().process(0, **fixture))

    def test_disabled_and_night_modes_are_silent(self) -> None:
        self.assertFalse(AlertModel(enabled=False).process(0, "disabled"))
        self.assertFalse(AlertModel(night=True).process(0, "night"))


if __name__ == "__main__":
    unittest.main()
