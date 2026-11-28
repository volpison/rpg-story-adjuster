from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from rpg_story_adjuster.model import Command, SourceLoc
from rpg_story_adjuster.commands import table
from rpg_story_adjuster.scriptscan import scan_script
from rpg_story_adjuster.walker import iter_project_commands

_TEXT_V = re.compile(r"\\V\[(\d+)\]", re.IGNORECASE)


@dataclass(frozen=True)
class Hit:
    source: SourceLoc
    kind: str                              # "switch" | "variable"
    via: str                               # "command" | "range" | "script" | "text"
    param_indices: tuple[int, ...]
    matched_id: int
    range_bounds: tuple[int, int] | None = None
    detail: str = ""


@dataclass(frozen=True)
class DynamicRef:
    source: SourceLoc
    kind: str
    via: str                               # "script" | "text"
    snippet: str
    reason: str


@dataclass
class ScanResult:
    hits: list[Hit] = field(default_factory=list)
    dynamic: list[DynamicRef] = field(default_factory=list)


def scan_commands(commands: Iterable[Command], kind: str, query_id: int) -> ScanResult:
    result = ScanResult()
    for cmd in commands:
        _scan_command(cmd, kind, query_id, result)
    return result


def scan_project(root: Path, kind: str, query_id: int) -> ScanResult:
    return scan_commands(iter_project_commands(root), kind, query_id)


def _scan_command(cmd: Command, kind: str, query_id: int, result: ScanResult) -> None:
    spec = table.get(cmd.code)
    if spec is None:
        return
    roles = spec.roles(cmd.parameters)

    end_role = next((r for r in roles if r.kind == f"{kind}_range_end"), None)
    for role in roles:
        if role.kind == f"{kind}_range_start" and end_role is not None:
            try:
                start = int(cmd.parameters[role.index])
                end = int(cmd.parameters[end_role.index])
            except (TypeError, ValueError, IndexError):
                continue
            lo, hi = min(start, end), max(start, end)
            if lo <= query_id <= hi:
                idxs = (role.index, end_role.index)
                if lo == hi:
                    result.hits.append(Hit(cmd.source, kind, "command", idxs, query_id))
                else:
                    result.hits.append(Hit(
                        cmd.source, kind, "range", idxs, query_id,
                        range_bounds=(lo, hi), detail=f"range {lo}..{hi}",
                    ))
        elif role.kind == kind:
            try:
                val = int(cmd.parameters[role.index])
            except (TypeError, ValueError, IndexError):
                continue
            if val == query_id:
                result.hits.append(Hit(
                    cmd.source, kind, "command", (role.index,), query_id,
                ))
        elif role.kind == "script":
            _scan_script_param(cmd, role, kind, query_id, result)
        elif role.kind == "text":
            _scan_text_param(cmd, role, kind, query_id, result)


def _scan_script_param(cmd: Command, role, kind: str, query_id: int, result: ScanResult) -> None:
    try:
        text = cmd.parameters[role.index]
    except IndexError:
        return
    if not isinstance(text, str):
        return
    for value, snippet, dynamic in scan_script(text, kind):
        if dynamic:
            result.dynamic.append(DynamicRef(
                cmd.source, kind, "script", snippet, "non-literal expression",
            ))
        elif value == query_id:
            result.hits.append(Hit(
                cmd.source, kind, "script", (role.index,), query_id, detail=snippet,
            ))


def _scan_text_param(cmd: Command, role, kind: str, query_id: int, result: ScanResult) -> None:
    if kind != "variable":
        return  # \V[n] is always a variable reference
    try:
        text = cmd.parameters[role.index]
    except IndexError:
        return
    texts = text if isinstance(text, list) else [text]
    for t in texts:
        if not isinstance(t, str):
            continue
        for m in _TEXT_V.finditer(t):
            if int(m.group(1)) == query_id:
                result.hits.append(Hit(
                    cmd.source, kind, "text", (role.index,), query_id,
                    detail=m.group(0),
                ))
