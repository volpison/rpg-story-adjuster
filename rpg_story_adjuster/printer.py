"""Pretty-print event commands as line-oriented text.

Format (per command):
    <indent>◆ <code>  <description>

- `<indent>` is 2 spaces per `indent` level (0 = no leading spaces).
- `<code>` is the MZ command code, always shown.
- `<description>` is code-specific; unknown codes fall back to `[raw] <repr>`.

Per-page header:
    # <file> · event <id> [· page <idx>]

The description format is round-trippable: strings use JSON double-quoted
literals (symmetric with json.loads), raw fallbacks use Python repr
(symmetric with ast.literal_eval). Phase 3 parser will consume this.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

from rpg_story_adjuster.model import Command
from rpg_story_adjuster.walker import iter_project_commands


_OP_122 = {0: "=", 1: "+=", 2: "-=", 3: "*=", 4: "/=", 5: "%="}
_COMPARE_111_VAR = {0: "==", 1: ">=", 2: "<=", 3: ">", 4: "<", 5: "!="}
_BG_101 = {0: "window", 1: "dim", 2: "transparent"}
_POS_101 = {0: "top", 1: "middle", 2: "bottom"}


def _quote(s) -> str:
    if not isinstance(s, str):
        return repr(s)
    return json.dumps(s, ensure_ascii=False)


def print_project(
    project_root: Path,
    *,
    file: str | None = None,
    event: int | None = None,
    page: int | None = None,
) -> str:
    """Pretty-print every command in the project (or a filtered subset)."""
    lines: list[str] = []
    last_loc: tuple = ()
    for cmd in iter_project_commands(project_root):
        if file and not cmd.source.file.endswith(file):
            continue
        if event is not None and cmd.source.event_id != event:
            continue
        if page is not None and cmd.source.page_index != page:
            continue
        loc = (cmd.source.file, cmd.source.event_id, cmd.source.page_index)
        if loc != last_loc:
            if lines:
                lines.append("")
            header = f"# {cmd.source.file} · event {cmd.source.event_id}"
            if cmd.source.page_index is not None:
                header += f" · page {cmd.source.page_index}"
            lines.append(header)
            last_loc = loc
        lines.append(_format_command(cmd))
    return "\n".join(lines) + "\n"


def print_commands(commands: Iterable[Command]) -> str:
    """Pretty-print a bare command list (used by tests)."""
    return "\n".join(_format_command(c) for c in commands) + "\n"


def _format_command(cmd: Command) -> str:
    indent = "  " * max(cmd.indent, 0)
    body = _describe(cmd)
    if body:
        return f"{indent}◆ {cmd.code}  {body}"
    return f"{indent}◆ {cmd.code}"


def _describe(cmd: Command) -> str:
    p = cmd.parameters
    code = cmd.code
    if code == 0:
        return ""
    if code == 101:
        return _desc_101(p)
    if code in (401, 108, 408, 355, 655):
        return _desc_text(p)
    if code == 102:
        return _desc_102(p)
    if code == 402:
        return _desc_402(p)
    if code in (403, 404):
        return ""
    if code == 117:
        return _desc_117(p)
    if code == 118:
        return _desc_118(p)
    if code == 119:
        return _desc_119(p)
    if code == 121:
        return _desc_121(p)
    if code == 122:
        return _desc_122(p)
    if code == 111:
        return _desc_111(p)
    if code in (411, 412):
        return "Else"
    return f"[raw] {p!r}"


def _desc_text(p) -> str:
    if not p or not isinstance(p[0], str):
        return f"[raw] {p!r}"
    return _quote(p[0])


def _desc_101(p) -> str:
    if len(p) < 5:
        return f"[raw] {p!r}"
    face_name, face_idx, bg, pos, name = p[0], p[1], p[2], p[3], p[4]
    bg_s = _BG_101.get(bg, str(bg))
    pos_s = _POS_101.get(pos, str(pos))
    face_s = f"{face_name}[{face_idx}]" if face_name else "-"
    name_s = _quote(name) if name else "-"
    return f"face={face_s} bg={bg_s} pos={pos_s} name={name_s}"


def _desc_102(p) -> str:
    if not p:
        return f"[raw] {p!r}"
    choices = p[0]
    if not isinstance(choices, list):
        return f"[raw] {p!r}"
    rendered = ", ".join(_quote(c) for c in choices)
    return f"choices=[{rendered}]"


def _desc_402(p) -> str:
    if not p:
        return ""
    idx = p[0]
    name = p[1] if len(p) > 1 else ""
    if name:
        return f"when choice {idx}: {_quote(name)}"
    return f"when choice {idx}"


def _desc_117(p) -> str:
    if not p:
        return f"[raw] {p!r}"
    return f"Common Event[{p[0]}]"


def _desc_118(p) -> str:
    if not p:
        return "Label"
    return f"Label {_quote(p[0])}"


def _desc_119(p) -> str:
    if not p:
        return "Jump"
    return f"Jump {_quote(p[0])}"


def _desc_121(p) -> str:
    if len(p) < 3:
        return f"[raw] {p!r}"
    start, end, value = p[0], p[1], p[2]
    state = "ON" if value == 0 else "OFF"
    if start == end:
        return f"Switches[{start}] = {state}"
    return f"Switches[{start}..{end}] = {state}"


def _desc_122(p) -> str:
    if len(p) < 5:
        return f"[raw] {p!r}"
    start, end = p[0], p[1]
    op = _OP_122.get(p[2], f"op{p[2]}")
    operand_type = p[4]
    operand = p[3]
    if operand_type == 1:
        operand_s = f"Variable[{operand}]"
    elif operand_type == 4:
        operand_s = f"script({_quote(operand)})"
    else:
        operand_s = str(operand)
    target = f"Variable[{start}]" if start == end else f"Variable[{start}..{end}]"
    return f"{target} {op} {operand_s}"


def _desc_111(p) -> str:
    if not p:
        return f"[raw] {p!r}"
    t = p[0]
    if t == 0 and len(p) >= 3:
        state = "ON" if p[2] == 0 else "OFF"
        return f"Switch[{p[1]}] is {state}"
    if t == 1 and len(p) >= 5:
        var_id = p[1]
        cmp_s = _COMPARE_111_VAR.get(p[2], f"cmp{p[2]}")
        operand = p[3]
        op_type = p[4]
        if op_type == 1:
            operand_s = f"Variable[{operand}]"
        elif op_type == 4:
            operand_s = f"script({_quote(operand)})"
        else:
            operand_s = str(operand)
        return f"Variable[{var_id}] {cmp_s} {operand_s}"
    if t == 2 and len(p) >= 3:
        state = "ON" if p[2] == 0 else "OFF"
        return f"Self Switch {p[1]!r} is {state}"
    if t == 12 and len(p) >= 2:
        return f"script({_quote(p[1])})"
    return f"[type {t}] {p!r}"