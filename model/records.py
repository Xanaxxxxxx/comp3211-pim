"""Immutable PIRs and their validation; no terminal or filesystem dependencies."""

from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
from typing import ClassVar

from .errors import ValidationError

HK_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Hong_Kong")
TEXT_FIELDS = frozenset({"text", "description", "name", "address", "mobile"})
TIME_FIELDS = frozenset({"deadline", "start", "alarm"})


def parse_time(value: str | datetime) -> datetime:
    """Accept ISO 8601 timestamps; interpret unspecified zones as Hong Kong."""
    if isinstance(value, str):
        # A date alone is ambiguous for deadlines, start times, and alarms.
        if "T" not in value and " " not in value:
            raise ValidationError("Use a date and time, e.g. 2026-11-20T20:00+08:00.")
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"Invalid date/time: {value!r}.") from exc
    if not isinstance(value, datetime):
        raise ValidationError("Date/time must be an ISO 8601 string or datetime.")
    try:
        if value.tzinfo is None:
            value = value.replace(tzinfo=HK_TIMEZONE)
        return value.astimezone(HK_TIMEZONE)
    except (ValueError, OverflowError) as exc:
        raise ValidationError("Date/time is out of range.") from exc


def require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be non-empty text.")


def require_id(value: object) -> None:
    if type(value) is not int or value < 1:
        raise ValidationError("Record ID must be a positive integer.")


@dataclass(frozen=True)
class Record:
    id: int
    kind: ClassVar[str]

    def __post_init__(self) -> None:
        require_id(self.id)
        for field in fields(self):
            if field.name in TEXT_FIELDS:
                require_text(getattr(self, field.name), field.name)
            elif field.name in TIME_FIELDS:
                object.__setattr__(self, field.name, parse_time(getattr(self, field.name)))

    def to_dict(self) -> dict:
        result = {"type": self.kind}
        for field in fields(self):
            value = getattr(self, field.name)
            result[field.name] = value.isoformat() if isinstance(value, datetime) else value
        return result

    def updated(self, changes: dict) -> "Record":
        editable = {field.name for field in fields(self)} - {"id"}
        if not changes:
            raise ValidationError("Provide at least one field to update.")
        unknown = set(changes) - editable
        if unknown:
            raise ValidationError(f"Fields cannot be updated: {', '.join(sorted(unknown))}.")
        return replace(self, **changes)


@dataclass(frozen=True)
class Note(Record):
    text: str
    kind: ClassVar[str] = "note"


@dataclass(frozen=True)
class Task(Record):
    description: str
    deadline: datetime
    kind: ClassVar[str] = "task"


@dataclass(frozen=True)
class Event(Record):
    description: str
    start: datetime
    alarm: datetime
    kind: ClassVar[str] = "event"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.alarm > self.start:
            raise ValidationError("Event alarm must be at or before the start time.")


@dataclass(frozen=True)
class Contact(Record):
    name: str
    address: str
    mobile: str
    kind: ClassVar[str] = "contact"


RECORD_TYPES = {cls.kind: cls for cls in (Note, Task, Event, Contact)}


def make_record(kind: str, record_id: int, data: dict) -> Record:
    if not isinstance(kind, str) or kind not in RECORD_TYPES:
        raise ValidationError("Record type must be note, task, event, or contact.")
    cls = RECORD_TYPES[kind]
    expected = {field.name for field in fields(cls)} - {"id"}
    supplied = set(data)
    if expected != supplied:
        missing, extra = expected - supplied, supplied - expected
        details = []
        if missing:
            details.append("missing: " + ", ".join(sorted(missing)))
        if extra:
            details.append("unexpected: " + ", ".join(sorted(extra)))
        raise ValidationError("Invalid fields (" + "; ".join(details) + ").")
    return cls(id=record_id, **data)
