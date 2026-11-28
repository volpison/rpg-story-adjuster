from __future__ import annotations
from pathlib import Path
from typing import Iterator

from rpg_story_adjuster.jsonio import load_json
from rpg_story_adjuster.model import Command, SourceLoc


def _commands_from_list(
    list_data: object,
    source_file: str,
    base_path: tuple,
    event_id: int | None = None,
    page_index: int | None = None,
) -> Iterator[Command]:
    if not isinstance(list_data, list):
        return
    for idx, entry in enumerate(list_data):
        if not isinstance(entry, dict):
            continue
        try:
            code = int(entry.get("code", -1))
            indent = int(entry.get("indent", 0))
        except (TypeError, ValueError):
            continue
        params = entry.get("parameters", [])
        if not isinstance(params, list):
            params = []
        yield Command(
            code=code,
            indent=indent,
            parameters=params,
            source=SourceLoc(
                file=source_file,
                event_id=event_id,
                page_index=page_index,
                command_index=idx,
                json_path=base_path + (idx,),
            ),
        )


def _rel(path: Path, project_root: Path) -> str:
    return str(path.relative_to(project_root)).replace("\\", "/")


def iter_map_commands(path: Path, project_root: Path) -> Iterator[Command]:
    loaded = load_json(path)
    data = loaded.data
    if not isinstance(data, dict):
        return
    events = data.get("events", [])
    if not isinstance(events, list):
        return
    rel = _rel(path, project_root)
    for event_idx, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_id = event.get("id", event_idx)
        if not isinstance(event_id, int):
            event_id = event_idx
        pages = event.get("pages", [])
        if not isinstance(pages, list):
            continue
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            yield from _commands_from_list(
                page.get("list", []), rel,
                base_path=("events", event_idx, "pages", page_index, "list"),
                event_id=event_id, page_index=page_index,
            )


def iter_common_event_commands(path: Path, project_root: Path) -> Iterator[Command]:
    loaded = load_json(path)
    data = loaded.data
    if not isinstance(data, list):
        return
    rel = _rel(path, project_root)
    for idx, ce in enumerate(data):
        if idx == 0 or not isinstance(ce, dict):
            continue
        ce_id = ce.get("id", idx)
        if not isinstance(ce_id, int):
            ce_id = idx
        yield from _commands_from_list(
            ce.get("list", []), rel,
            base_path=(idx, "list"),
            event_id=ce_id, page_index=None,
        )


def iter_troop_commands(path: Path, project_root: Path) -> Iterator[Command]:
    loaded = load_json(path)
    data = loaded.data
    if not isinstance(data, list):
        return
    rel = _rel(path, project_root)
    for idx, troop in enumerate(data):
        if idx == 0 or not isinstance(troop, dict):
            continue
        troop_id = troop.get("id", idx)
        if not isinstance(troop_id, int):
            troop_id = idx
        pages = troop.get("pages", [])
        if not isinstance(pages, list):
            continue
        for page_index, page in enumerate(pages):
            if not isinstance(page, dict):
                continue
            yield from _commands_from_list(
                page.get("list", []), rel,
                base_path=(idx, "pages", page_index, "list"),
                event_id=troop_id, page_index=page_index,
            )


def iter_project_commands(project_root: Path) -> Iterator[Command]:
    data_dir = project_root / "data"
    for p in sorted(data_dir.glob("Map*.json")):
        yield from iter_map_commands(p, project_root)
    ce = data_dir / "CommonEvents.json"
    if ce.exists():
        yield from iter_common_event_commands(ce, project_root)
    tr = data_dir / "Troops.json"
    if tr.exists():
        yield from iter_troop_commands(tr, project_root)