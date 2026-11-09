"""Translate command text into model operations without doing terminal I/O."""

from dataclasses import dataclass
import shlex

from model import PIM, ValidationError, load, save
from view.terminal import HELP, format_record, format_records


@dataclass(frozen=True)
class CommandResult:
    message: str = ""
    exit_requested: bool = False


def parse_id(value: str) -> int:
    try:
        record_id = int(value)
    except ValueError as exc:
        raise ValidationError("Record ID must be a positive integer.") from exc
    if record_id < 1:
        raise ValidationError("Record ID must be a positive integer.")
    return record_id


def parse_fields(arguments: list[str]) -> dict[str, str]:
    result = {}
    for argument in arguments:
        key, separator, value = argument.partition("=")
        if not separator or not key:
            raise ValidationError("Use field=value, with no spaces around =.")
        if key in result:
            raise ValidationError(f"Duplicate field: {key}.")
        result[key] = value
    return result


class Controller:
    def __init__(self, pim: PIM | None = None):
        self.pim = PIM() if pim is None else pim
        self.dirty = False

    def execute(self, line: str) -> CommandResult:
        line = line.strip()
        if not line or line.startswith("#"):
            return CommandResult()
        command, *remainder = line.split(maxsplit=1)
        raw_arguments = remainder[0] if remainder else ""
        # Preserve the quoted values in the search language for its own parser.
        if command == "search":
            return CommandResult(format_records(self.pim.search(raw_arguments)))
        try:
            arguments = shlex.split(raw_arguments)
        except ValueError as exc:
            raise ValidationError(f"Invalid command quoting: {exc}.") from exc
        if command == "help" and not arguments:
            return CommandResult(HELP)
        if command == "create" and arguments:
            record = self.pim.create(arguments[0], **parse_fields(arguments[1:]))
            self.dirty = True
            return CommandResult("Created " + format_record(record))
        if command == "update" and len(arguments) >= 2:
            record = self.pim.update(parse_id(arguments[0]), **parse_fields(arguments[1:]))
            self.dirty = True
            return CommandResult("Updated " + format_record(record))
        if command == "show" and len(arguments) == 1:
            return CommandResult(format_record(self.pim.get(parse_id(arguments[0]))))
        if command == "list" and not arguments:
            return CommandResult(format_records(self.pim.all()))
        if command == "delete" and len(arguments) == 1:
            record = self.pim.delete(parse_id(arguments[0]))
            self.dirty = True
            return CommandResult(f"Deleted record {record.id}.")
        if command == "save" and len(arguments) == 1:
            save(self.pim, arguments[0])
            self.dirty = False
            return CommandResult(f"Saved {len(self.pim.all())} record(s) to {arguments[0]}.")
        if command == "load" and (len(arguments) == 1 or
                                   (len(arguments) == 2 and arguments[1] == "--force")):
            if self.dirty and len(arguments) != 2:
                raise ValidationError("Unsaved changes. Save first, or use load PATH --force to discard them.")
            replacement = load(arguments[0])
            self.pim = replacement
            self.dirty = False
            return CommandResult(f"Loaded {len(self.pim.all())} record(s) from {arguments[0]}.")
        if command == "quit" and (not arguments or arguments == ["--force"]):
            if self.dirty and not arguments:
                raise ValidationError("Unsaved changes. Save first, or use quit --force to discard them.")
            return CommandResult("Goodbye.", exit_requested=True)
        raise ValidationError("Unknown command or incorrect arguments. Enter help for command formats.")
