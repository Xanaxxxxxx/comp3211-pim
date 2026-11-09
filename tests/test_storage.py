"""US10–11: round trips, hostile/corrupt files, and atomic save failures."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from model import PIM, StorageError, ValidationError, load, save


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "資料.pim"
        self.pim = PIM()
        self.pim.create("note", text="中文\nNote")
        self.pim.create("task", description="Submit", deadline="2026-11-20T20:00")
        self.pim.create("event", description="Meeting", start="2026-11-12T10:00",
                        alarm="2026-11-12T09:45")
        self.pim.create("contact", name="Chan", address="Hong Kong", mobile="00123")

    def test_roundtrip_all_fields_and_next_id_after_deletion(self):
        self.pim.delete(4)
        save(self.pim, self.path)
        restored = load(self.path)
        self.assertEqual(restored.all(), self.pim.all())
        self.assertEqual(restored.create("note", text="Next").id, 5)
        self.assertIn("中文", self.path.read_text(encoding="utf-8"))
        save(restored, self.path)
        self.assertEqual(load(self.path).snapshot(), restored.snapshot())

    def test_contact_roundtrip_and_empty_model(self):
        save(self.pim, self.path)
        self.assertEqual(load(self.path).get(4), self.pim.get(4))
        save(PIM(), self.path)
        self.assertEqual(load(self.path).all(), ())
        self.assertEqual(load(self.path).next_id, 1)

    def test_extension_and_missing_files(self):
        for suffix in (".json", "", ".pim.txt"):
            path = self.path.with_name("data" + suffix)
            with self.subTest(suffix=suffix), self.assertRaises(StorageError):
                save(self.pim, path)
            with self.assertRaises(StorageError):
                load(path)
        with self.assertRaises(StorageError):
            load(self.path)
        uppercase = self.path.with_suffix(".PIM")
        save(self.pim, uppercase)
        self.assertEqual(load(uppercase).all(), self.pim.all())
        with self.assertRaises(StorageError):
            save(self.pim, self.path.parent / "missing" / "data.pim")

    def test_invalid_snapshots_are_rejected(self):
        good = self.pim.snapshot()
        cases = [None, [], {}, {**good, "extra": 1}, {**good, "format": "other"},
                 {**good, "version": 2}, {**good, "version": True}, {**good, "next_id": 0},
                 {**good, "next_id": True}, {**good, "next_id": 1}, {**good, "records": {}},
                 {**good, "records": [None]}, {**good, "records": [{"type": "note"}]},
                 {**good, "records": [good["records"][0]] * 2}]
        for field, value in (("id", True), ("id", []), ("type", []), ("type", "other"),
                             ("text", None), ("text", ""), ("extra", "x")):
            invalid = copy.deepcopy(good)
            invalid["records"][0][field] = value
            cases.append(invalid)
        for snapshot in cases:
            with self.subTest(snapshot=snapshot), self.assertRaises(ValidationError):
                PIM.from_snapshot(snapshot)

    def test_corrupt_json_invalid_utf8_and_duplicate_keys_are_rejected(self):
        for content in (b"not json", b"\xff", b'{"format":1,"format":2}', b"[]",
                        b"[" * 1200 + b"]" * 1200):
            with self.subTest(content=content[:30]):
                self.path.write_bytes(content)
                with self.assertRaises(StorageError):
                    load(self.path)

    def test_failed_replace_preserves_original_file_and_cleans_temporary(self):
        save(self.pim, self.path)
        original = self.path.read_bytes()
        self.pim.create("note", text="Unsaved")
        with patch("model.storage.os.replace", side_effect=OSError("simulated write failure")):
            with self.assertRaises(StorageError):
                save(self.pim, self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_failed_temp_creation_and_failed_serialization_are_wrapped(self):
        with patch("model.storage.tempfile.NamedTemporaryFile", side_effect=OSError("no permission")):
            with self.assertRaises(StorageError):
                save(self.pim, self.path)
        with patch("model.storage.json.dump", side_effect=ValueError("simulated failure")):
            with self.assertRaises(StorageError):
                save(self.pim, self.path)
        self.assertEqual(list(self.path.parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
