"""Pure formatting functions shared by interactive and scripted sessions."""

import json
from model import Record

HELP = '''Commands (values containing spaces must be quoted):
  create note text="Buy milk"
  create task description="Submit project" deadline=2026-11-20T20:00
  create event description="Meeting" start=2026-11-12T10:00 alarm=2026-11-12T09:45
  create contact name="Chan Tai Man" address="Hong Kong" mobile="+852 9123 4567"
  update ID field=value [field=value ...]
  show ID                     Print one record with every field
  list                        Print all records with every field
  search EXPRESSION           Print all matching records with every field
  delete ID
  save "path/to/data.pim"      Save all records (replaces an existing file)
  load "path/to/data.pim" [--force]
  help
  quit [--force]              Exit; --force discards unsaved changes

Search examples:
  search type = task && deadline < "2026-11-21T00:00"
  search (text contains "milk" || name contains "Chan") && !(type = event)
Text fields: text, description, name, address, mobile. Operator: contains
Time fields: deadline, start, alarm. Operators: <, >, =
Type values: note, task, event, contact. Operator: =
Precedence: parentheses, !, &&, ||. Text matching ignores letter case.
Use double quotes for search text with spaces (JSON escapes are supported).
Times use ISO 8601; omitted timezone means Hong Kong (+08:00).
Alarms are stored event data; this program does not send notifications.
Load replaces all current records. Unsaved work requires --force to discard.
Changes stay in memory until save. No automatic saving on exit.'''


def format_record(record: Record) -> str:
    data = record.to_dict()
    lines = [f"[{record.id}] {record.kind}"]
    for key, value in data.items():
        if key not in {"id", "type"}:
            # Quoting preserves newlines and spaces in plain-text data unambiguously.
            lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines)


def format_records(records: tuple[Record, ...]) -> str:
    return "\n".join([f"{len(records)} record(s).", *(format_record(record) for record in records)])
