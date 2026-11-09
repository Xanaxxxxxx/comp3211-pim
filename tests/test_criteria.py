"""US7: every text/time field, Boolean connectors, precedence, and invalid syntax."""

import unittest
from model import CriteriaError, PIM
from model.criteria import parse_criteria


class CriteriaTests(unittest.TestCase):
    def setUp(self):
        self.pim = PIM()
        self.pim.create("note", text='Milk and bread\n香港 "notes" && other')
        self.pim.create("task", description="Submit PROJECT", deadline="2026-11-20T20:00")
        self.pim.create("event", description="Project meeting", start="2026-11-12T10:00",
                        alarm="2026-11-12T09:45")
        self.pim.create("contact", name="CHAN Tai Man", address="Hung Hom 香港", mobile="+852 00123456")

    def ids(self, expression):
        return [record.id for record in self.pim.search(expression)]

    def test_all_text_fields_and_case_insensitive_unicode_substrings(self):
        cases = {'text contains "milk"': [1], 'description contains "project"': [2, 3],
                 'name contains "chan"': [4], 'address contains "香港"': [4],
                 'mobile contains "0012"': [4], 'text contains "香港"': [1],
                 'text contains ""': [1], 'text contains "missing"': [],
                 'text contains "\\n"': [1], 'text contains "\\\"notes\\\""': [1],
                 'text contains "&&"': [1]}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.ids(expression), expected)

    def test_type_checks(self):
        for kind, expected in (("note", [1]), ("task", [2]), ("event", [3]), ("contact", [4])):
            self.assertEqual(self.ids(f"type = {kind}"), expected)

    def test_each_time_field_and_comparison(self):
        for field, record_id, value in (("deadline", 2, "2026-11-20T20:00"),
                                         ("start", 3, "2026-11-12T10:00"),
                                         ("alarm", 3, "2026-11-12T09:45")):
            for operator, comparison, expected in (("=", value, [record_id]),
                                                    ("<", "2026-12-01T00:00", [record_id]),
                                                    (">", "2026-01-01T00:00", [record_id]),
                                                    ("<", value, []), (">", value, [])):
                with self.subTest(field=field, operator=operator):
                    self.assertEqual(self.ids(f'{field} {operator} "{comparison}"'), expected)
        self.assertEqual(self.ids('deadline = "2026-11-20T12:00Z"'), [2])

    def test_nested_boolean_combinations_and_precedence(self):
        cases = {'type=note || type=task && description contains "missing"': [1],
                 '(type=note || type=task) && description contains "missing"': [],
                 '!(type=contact) && (text contains "milk" || description contains "project")': [1, 2, 3],
                 '!!(type=note)': [1], '!type=note && !type=task': [3, 4],
                 'type=note || type=task || type=event': [1, 2, 3],
                 'type=contact && name contains "chan" && address contains "hom"': [4],
                 '  type = note  ': [1]}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(self.ids(expression), expected)

    def test_absent_fields_are_false_and_negation_complements(self):
        self.assertEqual(self.ids('deadline < "2026-12-01T00:00"'), [2])
        self.assertEqual(self.ids('!(deadline < "2026-12-01T00:00")'), [1, 3, 4])

    def test_invalid_expressions_fail_even_when_no_records_exist(self):
        cases = [None, "", "  ", "x" * 4097, '"type" = note', "unknown = note",
                 'type "=" note', "type contains note", "type = alien", "text = x",
                 "start contains x", "deadline = bad", 'text contains "unterminated',
                 'text contains "\\q"', "type =", "type", "type = &&", "!", "()",
                 "(type = note", "type = note)", "type = note garbage", "type = note & type = task",
                 "type = note | type = task", "type = note &&", "type = note ||",
                 'text contains \\foo', '"contains"', "!" * 52 + "type = note",
                 "(" * 52 + "type = note" + ")" * 52]
        for expression in cases:
            with self.subTest(expression=expression), self.assertRaises(CriteriaError):
                PIM().search(expression)

    def test_compiled_criterion_is_reusable(self):
        criterion = parse_criteria("type=note")
        self.assertTrue(criterion.matches(self.pim.get(1)))
        self.assertFalse(criterion.matches(self.pim.get(2)))


if __name__ == "__main__":
    unittest.main()
