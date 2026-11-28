from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceLoc:
    file: str                    # e.g. "data/Map001.json" (project-relative)
    event_id: int | None = None       # None when not inside a map event
    page_index: int | None = None     # None when not on a map page
    command_index: int | None = None  # index within the owning command list
    json_path: tuple = ()             # path from root of the file to the Command dict


@dataclass
class Command:
    code: int
    indent: int
    parameters: list
    source: SourceLoc