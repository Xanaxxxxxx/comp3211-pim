"""Application model and transactional in-memory record operations."""

from .criteria import parse_criteria
from .errors import RecordNotFound, ValidationError
from .records import Record, make_record, require_id


class PIM:
    def __init__(self):
        self._records: dict[int, Record] = {}
        self._next_id = 1

    @property
    def next_id(self) -> int:
        return self._next_id

    def create(self, kind: str, /, **data) -> Record:
        record = make_record(kind, self._next_id, data)
        self._records[record.id] = record
        self._next_id += 1
        return record

    def get(self, record_id: int) -> Record:
        require_id(record_id)
        try:
            return self._records[record_id]
        except KeyError as exc:
            raise RecordNotFound(f"Record {record_id} does not exist.") from exc

    def all(self) -> tuple[Record, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def update(self, record_id: int, /, **changes) -> Record:
        record = self.get(record_id).updated(changes)
        self._records[record_id] = record
        return record

    def delete(self, record_id: int) -> Record:
        record = self.get(record_id)
        del self._records[record_id]
        return record

    def search(self, expression: str) -> tuple[Record, ...]:
        criterion = parse_criteria(expression)
        return tuple(record for record in self.all() if criterion.matches(record))

    def snapshot(self) -> dict:
        return {"format": "COMP3211-PIM", "version": 1, "next_id": self.next_id,
                "records": [record.to_dict() for record in self.all()]}

    @classmethod
    def from_snapshot(cls, snapshot: object) -> "PIM":
        if not isinstance(snapshot, dict) or set(snapshot) != {"format", "version", "next_id", "records"}:
            raise ValidationError("Invalid PIM file structure.")
        if snapshot["format"] != "COMP3211-PIM" or type(snapshot["version"]) is not int or snapshot["version"] != 1:
            raise ValidationError("Unsupported PIM file format/version.")
        require_id(snapshot["next_id"])
        if not isinstance(snapshot["records"], list):
            raise ValidationError("Records must be a list.")
        result = cls()
        for item in snapshot["records"]:
            if not isinstance(item, dict) or "id" not in item or "type" not in item:
                raise ValidationError("Each record must include id and type.")
            data = {key: value for key, value in item.items() if key not in {"id", "type"}}
            record = make_record(item["type"], item["id"], data)
            if record.id in result._records:
                raise ValidationError(f"Duplicate record ID: {record.id}.")
            result._records[record.id] = record
        if result._records and snapshot["next_id"] <= max(result._records):
            raise ValidationError("next_id must exceed all stored record IDs.")
        result._next_id = snapshot["next_id"]
        return result
