from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class Backend:
    """Everything one object-storage backend contributes, as plain data.

    Tutor has no concept of a "backend" - plugin.py reads these fields to
    build its own CONFIG_DEFAULTS/CONFIG_UNIQUE registrations, prefixed
    OBJSTORAGE_<NAME>_. Patches and init-task scripts are deliberately NOT
    listed here: they're discovered by directory/filename convention
    (patches/<name>/*, templates/objectstorage/tasks/objectstorage/<name>.sh),
    so adding a patch file costs zero Python changes.
    """

    name: str
    defaults: dict[str, t.Any]
    unique: dict[str, t.Any] = dataclasses.field(default_factory=dict)
    requires_ack_key: str | None = None
