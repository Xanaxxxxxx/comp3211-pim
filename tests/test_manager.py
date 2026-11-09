"""US6–9: record identity, retrieval, modification, and deletion."""

import unittest
from model import PIM, RecordNotFound, ValidationError


class ManagerTests(unittest.TestCase):
    def test_list_get_update_delete_and_ids_never_reused(self):
        pim = PIM()
        self.assertEqual(pim.all(), ())
        first = pim.create("note", text="First")
        second = pim.create("note", text="Second")
        self.assertEqual(pim.all(), (first, second))
        changed = pim.update(second.id, text="Changed")
        self.assertEqual(pim.get(second.id).text, "Changed")
        self.assertEqual(pim.delete(first.id), first)
        self.assertEqual(pim.all(), (changed,))
        third = pim.create("note", text="Third")
        self.assertEqual(third.id, 3)
        self.assertEqual(pim.next_id, 4)

    def test_missing_record_operations_fail_without_modifying_records(self):
        pim = PIM()
        for operation in (lambda: pim.get(1), lambda: pim.update(1, text="x"), lambda: pim.delete(1)):
            with self.assertRaises(RecordNotFound):
                operation()
            self.assertEqual(pim.all(), ())
        with self.assertRaises(ValidationError):
            pim.get(True)

    def test_snapshot_is_detached_and_reconstructs_sorted_records(self):
        pim = PIM()
        pim.create("note", text="First")
        pim.create("note", text="Second")
        snapshot = pim.snapshot()
        snapshot["records"].reverse()
        restored = PIM.from_snapshot(snapshot)
        self.assertEqual(restored.all(), pim.all())
        self.assertEqual(restored.next_id, 3)
        snapshot["records"][0]["text"] = "External change"
        self.assertEqual(pim.get(2).text, "Second")
        self.assertEqual(restored.get(2).text, "Second")


if __name__ == "__main__":
    unittest.main()
