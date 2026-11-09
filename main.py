"""CLI entry point. Run with Python 3.10+; no external dependencies."""

import argparse
import sys
from typing import TextIO

from controller.commands import Controller
from model import PIMError, load


def run_session(controller: Controller, source: TextIO, interactive: bool) -> int:
    errors = False
    if interactive:
        print("Personal Information Manager | Enter help for commands.")
    while True:
        try:
            if interactive:
                print("pim> ", end="", flush=True)
            line = source.readline()
            if not line:
                if controller.dirty:
                    print("ERROR: Input ended with unsaved changes; changes were not saved.", file=sys.stderr)
                    return 1
                break
            result = controller.execute(line)
            if result.message:
                print(result.message)
            if result.exit_requested:
                break
        except PIMError as exc:
            errors = True
            print(f"ERROR: {exc}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nInterrupted; unsaved changes were not saved.", file=sys.stderr)
            return 130
    return int(errors) if not interactive else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Command-line personal information manager.")
    parser.add_argument("--file", help="Load an existing .pim file before starting")
    parser.add_argument("--script", help="Read commands from a UTF-8 file instead of standard input")
    args = parser.parse_args(argv)
    try:
        controller = Controller(load(args.file) if args.file else None)
        if args.script:
            with open(args.script, encoding="utf-8") as source:
                return run_session(controller, source, False)
        return run_session(controller, sys.stdin, sys.stdin.isatty())
    except (PIMError, OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
