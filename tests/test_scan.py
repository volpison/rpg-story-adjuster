import json
from pathlib import Path

import pytest

from rpg_story_adjuster.scan import scan_project


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def _mkproject(tmp_path: Path, commands: list[dict]) -> Path:
    _write(tmp_path / "data" / "Map001.json", {
        "events": [None, {"id": 1, "pages": [{"list": commands}]}],
    })
    return tmp_path


def test_switch_literal_in_121_and_111(tiny_project: Path):
    r = scan_project(tiny_project, "switch", 10)
    assert len(r.hits) == 2
    via = sorted(h.via for h in r.hits)
    assert via == ["command", "command"]
    idxs = sorted(h.param_indices for h in r.hits)
    assert idxs == [(0, 1), (1,)]              # 121 degenerate range + 111 switch slot


def test_variable_operand_in_122(tiny_project: Path):
    # CommonEvents has [5,5,0,3,1] - operand_type=1 means operand is variable 3
    r = scan_project(tiny_project, "variable", 3)
    assert len(r.hits) == 1
    assert r.hits[0].param_indices == (3,)
    # variable 5 (the start=end) also hits
    r2 = scan_project(tiny_project, "variable", 5)
    assert len(r2.hits) == 1


def test_non_degenerate_range_is_flagged_as_range(tmp_path: Path):
    p = _mkproject(tmp_path, [
        {"code": 121, "indent": 0, "parameters": [8, 12, 0]},
        {"code": 0, "indent": 0, "parameters": []},
    ])
    r = scan_project(p, "switch", 10)
    assert len(r.hits) == 1
    h = r.hits[0]
    assert h.via == "range"
    assert h.range_bounds == (8, 12)


def test_script_literal_vs_dynamic(tmp_path: Path):
    p = _mkproject(tmp_path, [
        {"code": 355, "indent": 0,
         "parameters": ["$gameSwitches.setValue(10, true)"]},
        {"code": 355, "indent": 0,
         "parameters": ["$gameSwitches.value(10+1)"]},
        {"code": 355, "indent": 0,
         "parameters": ["$gameSwitches.value(x)"]},
        {"code": 0, "indent": 0, "parameters": []},
    ])
    r = scan_project(p, "switch", 10)
    assert len(r.hits) == 1
    assert r.hits[0].via == "script"
    assert len(r.dynamic) == 2


def test_text_code_in_401(tmp_path: Path):
    p = _mkproject(tmp_path, [
        {"code": 401, "indent": 0, "parameters": ["Gold: \\V[5] coins"]},
        {"code": 0, "indent": 0, "parameters": []},
    ])
    r = scan_project(p, "variable", 5)
    assert len(r.hits) == 1
    assert r.hits[0].via == "text"
    assert r.hits[0].detail == "\\V[5]"


def test_transfer_player_direct_vs_variable(tmp_path: Path):
    p = _mkproject(tmp_path, [
        {"code": 201, "indent": 0, "parameters": [0, 2, 16, 0, 0, 0]},
        {"code": 201, "indent": 0, "parameters": [1, 7, 8, 9, 0, 0]},
        {"code": 0, "indent": 0, "parameters": []},
    ])
    assert len(scan_project(p, "variable", 2).hits) == 0   # direct map id, not a var
    assert len(scan_project(p, "variable", 8).hits) == 1   # designation 1 -> var at idx 2

def test_variable_comparison_in_111(tmp_path: Path):
    # Conditional Branch: variable 4 == variable 10 (operand_type=1).
    # MZ format is [1, var_left, comparison, operand, operand_type],
    # NOT [1, var_left, operand, comparison, operand_type].
    p = _mkproject(tmp_path, [
        {"code": 111, "indent": 0, "parameters": [1, 4, 0, 10, 1]},
        {"code": 0, "indent": 0, "parameters": []},
    ])
    assert len(scan_project(p, "variable", 4).hits) == 1   # left side
    assert len(scan_project(p, "variable", 10).hits) == 1  # right side (operand_type=1)
    assert len(scan_project(p, "variable", 0).hits) == 0   # comparison op, not a var


def test_variable_comparison_against_constant_in_111(tmp_path: Path):
    # [1, var_id, comparison, constant, operand_type=0] — right side is a literal.
    p = _mkproject(tmp_path, [
        {"code": 111, "indent": 0, "parameters": [1, 10, 0, 1, 0]},
        {"code": 0, "indent": 0, "parameters": []},
    ])
    assert len(scan_project(p, "variable", 10).hits) == 1
    assert len(scan_project(p, "variable", 1).hits) == 0   # constant, not a var
    