"""Surgical JSON writer: replace specific numbers in a file, touching only their bytes.

Designed for hand-formatted RPG Maker MZ data. Never re-serializes the whole
file, so newlines/whitespace/key-order that the game or a tool produced
survive byte-for-byte outside the target spans.
"""
from __future__ import annotations
from pathlib import Path

from rpg_story_adjuster.span import parse_with_spans


class SurgicalError(Exception):
    pass


def patch_numbers_in_file(
    path: Path,
    patches: list[tuple[tuple, int, int]],
) -> None:
    """Apply (json_path, old_value, new_value) tuples to `path` atomically.

    All patches validated before any byte is written. After patching, re-parses
    and confirms: (a) file parses cleanly, (b) only `patches`' paths changed.
    Rolls back (writes original bytes back) on any failure.
    """
    if not patches:
        return

    original = path.read_bytes()
    parsed_before, spans = parse_with_spans(original)

    edits: list[tuple[int, int, bytes]] = []
    for json_path, old_value, new_value in patches:
        if json_path not in spans:
            raise SurgicalError(f"path {json_path} not found in {path}")
        start, end = spans[json_path]
        try:
            current = int(original[start:end])
        except ValueError:
            raise SurgicalError(
                f"path {json_path} in {path} is not an int: "
                f"{original[start:end]!r}"
            )
        if current != old_value:
            raise SurgicalError(
                f"path {json_path} in {path}: expected {old_value}, "
                f"found {current} (file changed since scan?)"
            )
        edits.append((start, end, str(new_value).encode("ascii")))

    # Apply descending by start so earlier spans stay valid.
    edits.sort(key=lambda e: e[0], reverse=True)
    out = bytearray(original)
    for start, end, new_bytes in edits:
        out[start:end] = new_bytes
    patched = bytes(out)

    try:
        parsed_after, _ = parse_with_spans(patched)
    except Exception as e:
        raise SurgicalError(f"patched content fails to parse: {e}")

    allowed = {p for p, _, _ in patches}
    _verify_only_allowed_changed(parsed_before, parsed_after, (), allowed)
    for json_path, _, new_value in patches:
        _assert_value(parsed_after, json_path, new_value)

    tmp = path.with_suffix(path.suffix + ".rpgadj.tmp")
    tmp.write_bytes(patched)
    tmp.replace(path)


def _assert_value(tree, path: tuple, expected) -> None:
    cur = tree
    for step in path:
        try:
            cur = cur[step]
        except (KeyError, IndexError, TypeError):
            raise SurgicalError(f"path {path} missing after patch")
    if cur != expected:
        raise SurgicalError(f"path {path}: expected {expected!r}, got {cur!r}")


def _verify_only_allowed_changed(before, after, cur: tuple, allowed: set) -> None:
    if cur in allowed:
        return
    if type(before) is not type(after):
        raise SurgicalError(
            f"type changed at {cur}: {type(before).__name__} -> {type(after).__name__}"
        )
    if isinstance(before, dict):
        if set(before) != set(after):
            raise SurgicalError(f"keys changed at {cur}")
        for k in before:
            _verify_only_allowed_changed(before[k], after[k], cur + (k,), allowed)
    elif isinstance(before, list):
        if len(before) != len(after):
            raise SurgicalError(f"length changed at {cur}")
        for i, (b, a) in enumerate(zip(before, after)):
            _verify_only_allowed_changed(b, a, cur + (i,), allowed)
    else:
        if before != after:
            raise SurgicalError(
                f"unexpected change at {cur}: {before!r} -> {after!r}"
            )