"""CLI contract checks beyond the required model unit tests."""

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from controller.commands import Controller
from main import main, run_session
from model import PIM, PIMError, ValidationError, save


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.controller = Controller()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "my records.pim"

    def test_complete_session(self):
        c = self.controller
        self.assertEqual(c.execute("# comment").message, "")
        self.assertEqual(c.execute(" ").message, "")
        self.assertIn("Commands", c.execute("help").message)
        self.assertIn("0 record(s)", c.execute("list").message)
        self.assertIn("Created [1] note", c.execute('create note text="Hello World"').message)
        self.assertIn("Created [2] task", c.execute('create task description="Due Soon" deadline=2026-11-20T20:00').message)
        self.assertIn("Hello World", c.execute("show 1").message)
        self.assertIn("1 record(s)", c.execute('search text contains "hello world"').message)
        self.assertIn("Updated [1] note", c.execute('update 1 text="Changed"').message)
        self.assertIn("Deleted record 2", c.execute("delete 2").message)
        self.assertTrue(c.dirty)
        self.assertIn("Saved 1", c.execute(f'save "{self.path}"').message)
        self.assertFalse(c.dirty)
        c.execute("delete 1")
        self.assertIn("Loaded 1", c.execute(f'load "{self.path}" --force').message)
        self.assertFalse(c.dirty)
        self.assertIn("Changed", c.execute("show 1").message)
        self.assertTrue(c.execute("quit").exit_requested)

    def test_unsaved_changes_guard_and_failed_load_preserve_state(self):
        c = self.controller
        c.execute('create note text="Keep me"')
        before = c.pim.snapshot()
        for command in ("quit", f'load "{self.path}"', f'load "{self.path}" --force'):
            with self.subTest(command=command), self.assertRaises(PIMError):
                c.execute(command)
            self.assertEqual(c.pim.snapshot(), before)
            self.assertTrue(c.dirty)
        self.assertTrue(c.execute("quit --force").exit_requested)
        save(PIM(), self.path)
        c.execute(f'load "{self.path}" --force')
        self.assertEqual(c.pim.all(), ())

    def test_invalid_commands_are_recoverable(self):
        cases = ["unknown", "help extra", "create", "create note", 'create note text="bad',
                 "create note text=x text=y", "create note text=x kind=task",
                 "create note text=x id=9", "create note =x", "create note text",
                 "show zero", "show 0", "show 1 extra", "list extra", "update 1",
                 "delete", "save", "load", "load x.pim --invalid", "quit extra"]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(PIMError):
                self.controller.execute(command)
            self.assertFalse(self.controller.dirty)
        self.controller.execute("create note text=x")
        with self.assertRaises(ValidationError):
            self.controller.execute("update 1 record_id=8")
        self.assertEqual(self.controller.pim.get(1).text, "x")

    def test_clean_load_and_failed_save(self):
        save(PIM(), self.path)
        self.assertIn("Loaded 0", self.controller.execute(f'load "{self.path}"').message)
        self.controller.execute("create note text=x")
        with self.assertRaises(PIMError):
            self.controller.execute('save "wrong.json"')
        self.assertTrue(self.controller.dirty)

    def test_script_errors_go_to_stderr_and_session_continues(self):
        output, errors = io.StringIO(), io.StringIO()
        source = io.StringIO('bad-command\ncreate note text="still works"\nlist\nquit --force\n')
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = run_session(self.controller, source, False)
        self.assertEqual(status, 1)
        self.assertIn("ERROR:", errors.getvalue())
        self.assertIn("still works", output.getvalue())

    def test_eof_with_unsaved_changes_reports_failure(self):
        errors = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            status = run_session(self.controller, io.StringIO("create note text=x\n"), False)
        self.assertEqual(status, 1)
        self.assertIn("unsaved", errors.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_session(Controller(), io.StringIO(""), False), 0)

    def test_main_script_and_startup_errors(self):
        script = self.path.with_suffix(".txt")
        script.write_text(f'create note text="Scripted"\nsave "{self.path}"\nquit\n', encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--script", str(script)]), 0)
            self.assertEqual(main(["--file", str(self.path), "--script", str(script)]), 0)
        for args in (["--file", "missing.pim"], ["--script", "missing.txt"]):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 1)

    def test_documented_demo_runs_in_a_real_process(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / "main.py"), "--script",
                                 str(root / "examples" / "demo.txt")],
                                cwd=self.temporary.name, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Loaded 4 record(s)", result.stdout)
        self.assertIn("Goodbye.", result.stdout)


if __name__ == "__main__":
    unittest.main()
