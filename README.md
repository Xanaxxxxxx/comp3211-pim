# COMP3211 Personal Information Manager

A command-line PIM for notes, tasks, events, and contacts. Written in Python using only standard libraries. All domain logic, validation, search, and persistence are in `model/`.

## Start

Developed and tested on macOS with Python 3.13.0. Python 3.10 or later is required. There are no packages to install and no compilation step.

From this folder:

```sh
python3 main.py
```

Enter `help` for all commands. A short session:

```text
create note text="Project ideas"
create task description="Submit project" deadline=2026-11-20T20:00
search type = task && deadline < "2026-11-21T00:00"
save "my-records.pim"
quit
```

Start with saved records:

```sh
python3 main.py --file "my-records.pim"
```

Run the supplied demonstration:

```sh
python3 main.py --script examples/demo.txt
```

The demo writes/replaces `demo.pim` in the current working directory. It uses fictional data.

## Verify

```sh
python3 -m unittest discover -s tests -v
python3 tools/measure_coverage.py
python3 -m compileall -q main.py model controller view tests tools
```

The coverage command regenerates `TEST_COVERAGE.md` and annotated line details under `.coverage/`. The supplied PDF is a snapshot of the measured results; update it if you change the program or tests.

## Contents

| Location | Purpose |
| --- | --- |
| `main.py` | Interactive and script entry point |
| `model/records.py` | Immutable typed records and field/time validation |
| `model/criteria.py` | Search parser and criterion evaluation |
| `model/manager.py` | CRUD, IDs, search, snapshots |
| `model/storage.py` | Atomic .pim saving and validated loading |
| `model/errors.py` | Expected domain and storage exceptions |
| `controller/commands.py` | Command handling and unsaved-change state |
| `view/terminal.py` | Help and detailed record output |
| `tests/` | Model unit tests and additional CLI checks |
| `examples/demo.txt` | Runnable demonstration commands |
| `DEVELOPER_MANUAL.pdf` | Build, debugging, architecture and tests |
| `USER_MANUAL.pdf` | Commands, search, file operations and errors |
| `REQUIREMENTS_COVERAGE.pdf` | US1-US11 and implementation rule mapping |
| `TEST_COVERAGE.pdf` | Measured model line coverage |

## Decisions to align with your SRS

All text fields are required and must contain at least one non-whitespace character; original text is preserved. A contact mobile number is stored as text, preserving leading zeros, country codes, and spaces. An event alarm must be at or before its start. Date/time inputs require both date and time. Missing timezones mean Hong Kong (+08:00); explicit offsets are converted to Hong Kong time. Text searches are case-insensitive substring matches. A predicate on an absent field is false; negation reverses that result. Files replace the complete record collection on load. IDs are positive, stable and not reused within a saved record collection. Alarms are stored/searchable timestamps; background notifications are outside this implementation.

No existing group SRS or source code was supplied. The requirements coverage document maps the assignment's user stories and declares the implementation rules above; align those rules and identifiers with your group's final SRS.

## Submission scope and AI acknowledgement

This folder contains the coding portion, unit tests, and implementation/test documentation. It does not contain the group's full SRS, formal design document, demonstration MP4, presentation slides/recording, or completed Honour Declaration. The short architecture description is developer documentation, not a replacement for the assignment's required design diagrams.

The implementation, tests, and accompanying documentation were prepared with OpenAI Codex assistance. Record this actual use in the supplied Honour Declaration. Group members must review and understand the code, decide their actual contributions, and complete their own names, IDs, signatures and dates. The declaration template has not been modified.
