import json
from pathlib import Path

import pytest

from rpg_story_adjuster.jsonio_surgical import (
    patch_numbers_in_file, SurgicalError,
)


def _write_handformatted(path: Path) -> None:
    """Emulate the WindsRhapsody format: newline after '{', after top-level ','."""
    path.write_bytes(
        b'{\n"autoplayBgm":false,"width":27,\n'
        b'"events":[null,{"id":1,"pages":[{"list":['
        b'{"code":121,"indent":0,"parameters":[10,10,0]},'
        b'{"code":0,"indent":0,"parameters":[]}]}]}]}'
    )


def test_patch_one_number_preserves_all_other_bytes(tmp_path: Path):
    p = tmp_path / "Map001.json"
    _write_handformatted(p)
    before = p.read_bytes()

    path = ("events", 1, "pages", 0, "list", 0, "parameters", 0)
    patch_numbers_in_file(p, [(path, 10, 47)])

    after = p.read_bytes()
    # Same length minus one char (10 -> 47 same length); verify by diff.
    assert b'[10,10,0]' in before
    assert b'[47,10,0]' in after
    # Everything outside the changed number is identical.
    i_before = before.index(b'[10,10,0]')
    i_after = after.index(b'[47,10,0]')
    assert before[:i_before] == after[:i_after]
    assert before[i_before + 9:] == after[i_after + 9:]


def test_patch_two_numbers_in_one_command(tmp_path: Path):
    p = tmp_path / "Map001.json"
    _write_handformatted(p)
    path = ("events", 1, "pages", 0, "list", 0, "parameters")
    patch_numbers_in_file(p, [
        (path + (0,), 10, 47),
        (path + (1,), 10, 47),
    ])
    assert b'[47,47,0]' in p.read_bytes()


def test_patch_refuses_wrong_old_value(tmp_path: Path):
    p = tmp_path / "Map001.json"
    _write_handformatted(p)
    with pytest.raises(SurgicalError, match="expected 99"):
        patch_numbers_in_file(p, [
            (("events", 1, "pages", 0, "list", 0, "parameters", 0), 99, 47),
        ])


def test_patch_is_length_agnostic(tmp_path: Path):
    p = tmp_path / "Map001.json"
    _write_handformatted(p)
    patch_numbers_in_file(p, [
        (("events", 1, "pages", 0, "list", 0, "parameters", 0), 10, 4712),
    ])
    assert b'[4712,10,0]' in p.read_bytes()


def test_noop_when_no_patches(tmp_path: Path):
    p = tmp_path / "Map001.json"
    _write_handformatted(p)
    before = p.read_bytes()
    patch_numbers_in_file(p, [])
    assert p.read_bytes() == before