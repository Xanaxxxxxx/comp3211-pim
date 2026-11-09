"""Versioned JSON .pim persistence with atomic replacement and strict loading."""

import json
import os
from pathlib import Path
import tempfile

from .errors import StorageError, ValidationError
from .manager import PIM


def pim_path(path: str | Path) -> Path:
    result = Path(path).expanduser()
    if result.suffix.lower() != ".pim":
        raise StorageError("File extension must be .pim.")
    return result


def save(pim: PIM, path: str | Path) -> None:
    """Replace destination only after a complete, flushed UTF-8 write."""
    destination = pim_path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".pim-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(pim.snapshot(), stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except (OSError, ValueError) as exc:
        raise StorageError(f"Cannot save {destination}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON key: {key}.")
        result[key] = value
    return result


def load(path: str | Path) -> PIM:
    """Build a new validated model; the caller's current model stays untouched."""
    source = pim_path(path)
    try:
        with source.open(encoding="utf-8") as stream:
            data = json.load(stream, object_pairs_hook=unique_object)
        return PIM.from_snapshot(data)
    except (OSError, UnicodeError, ValueError, RecursionError, ValidationError) as exc:
        raise StorageError(f"Cannot load {source}: {exc}") from exc
