"""US1–6: field validation, typed PIRs, and immutable validated updates."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import unittest

from model import Contact, Event, Note, PIM, Task, ValidationError, parse_time


class RecordTests(unittest.TestCase):
    def test_all_types_and_fields_are_preserved(self):
        pim = PIM()
        note = pim.create("note", text="  筆記\n第二行  ")
        task = pim.create("task", description="Submit", deadline="2026-11-20T20:00")
        event = pim.create("event", description="Meet", start="2026-11-12T10:00",
                           alarm="2026-11-12T09:45")
        contact = pim.create("contact", name="陳同學", address="香港", mobile="00123456")
        self.assertIsInstance(note, Note)
        self.assertIsInstance(task, Task)
        self.assertIsInstance(event, Event)
        self.assertIsInstance(contact, Contact)
        self.assertEqual(note.text, "  筆記\n第二行  ")
        self.assertEqual(contact.mobile, "00123456")
        self.assertEqual(task.to_dict(), {"id": 2, "type": "task", "description": "Submit",
                                          "deadline": "2026-11-20T20:00:00+08:00"})

    def test_datetimes_normalize_to_hong_kong(self):
        expected = parse_time("2026-11-20T20:00")
        for value in ("2026-11-20T12:00Z", "2026-11-20 20:00:00+08:00",
                      datetime(2026, 11, 20, 12, tzinfo=timezone.utc), datetime(2026, 11, 20, 20)):
            with self.subTest(value=value):
                self.assertEqual(parse_time(value), expected)
                self.assertEqual(parse_time(value).isoformat(), "2026-11-20T20:00:00+08:00")

    def test_invalid_times_are_rejected(self):
        for value in ("2026-11-20", "not a date", "2026-02-30T12:00", "2026-11-20T25:00",
                      None, 123, "", "0001-01-01T00:00+14:00"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_time(value)

    def test_required_text_and_ids_are_validated(self):
        for text in ("", " \n", None, 123, []):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                Note(1, text)
        for record_id in (0, -1, True, 1.0, "1", None, []):
            with self.subTest(record_id=record_id), self.assertRaises(ValidationError):
                Note(record_id, "Text")

    def test_creation_rejects_invalid_types_and_fields_without_consuming_id(self):
        pim = PIM()
        cases = [("bad", {}), (None, {}), ([], {}), ("task", {"description": "x"}),
                 ("note", {"text": "x", "extra": "y"}), ("note", {}),
                 ("note", {"kind": "x", "text": "x"}), ("note", {"id": 9, "text": "x"})]
        for kind, data in cases:
            with self.subTest(kind=kind, data=data), self.assertRaises(ValidationError):
                pim.create(kind, **data)
            self.assertEqual(pim.next_id, 1)
            self.assertEqual(pim.all(), ())

    def test_alarm_at_start_allowed_but_after_start_rejected(self):
        pim = PIM()
        event = pim.create("event", description="Meeting", start="2026-11-12T10:00",
                           alarm="2026-11-12T10:00")
        self.assertEqual(event.start, event.alarm)
        with self.assertRaises(ValidationError):
            pim.update(event.id, alarm="2026-11-12T10:01")
        self.assertEqual(pim.get(event.id), event)

    def test_updates_are_immutable_and_validate_all_changes_together(self):
        pim = PIM()
        event = pim.create("event", description="Old", start="2026-11-12T10:00",
                           alarm="2026-11-12T09:45")
        updated = pim.update(1, description="New", start="2026-11-12T09:00", alarm="2026-11-12T08:45")
        self.assertEqual(updated.id, event.id)
        self.assertEqual(updated.description, "New")
        self.assertEqual(event.description, "Old")
        with self.assertRaises(FrozenInstanceError):
            updated.description = "Mutated"
        for changes in ({}, {"id": 2}, {"kind": "note"}, {"start": "bad time"},
                        {"description": ""}, {"record_id": 8}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                pim.update(1, **changes)
            self.assertEqual(pim.get(1), updated)


if __name__ == "__main__":
    unittest.main()
