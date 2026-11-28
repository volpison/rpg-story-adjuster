import json
from pathlib import Path

import pytest

from rpg_story_adjuster.apply import build_plan, apply_plan, ReassignError
from rpg_story_adjuster.scan import scan_project


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(data, separators=(",", ":")).encode("utf-8")
    )


def _proj_with_switch(tmp_path: Path, sw: int) -> Path:
    data = tmp_path / "data"
    _write(data / "Map001.json", {
        "events": [None, {"id": 1, "pages": [{"list": [
            {"code": 121, "indent": 0, "parameters": [sw, sw, 0]},
            {"code": 0, "indent": 0, "parameters": []},
        ]}]}],
    })
    return tmp_path


def test_dry_run_plan_lists_patches(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    plan = build_plan(root, "switch", 10, 47)
    assert sum(len(v) for v in plan.patches_by_file.values()) == 2
    assert plan.warnings == []


def test_apply_moves_id_and_verifies_post(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    before = scan_project(root, "switch", 10)
    assert len(before.hits) == 1     # degenerate range counts as one hit
    plan = build_plan(root, "switch", 10, 47)
    apply_plan(root, plan)
    assert len(scan_project(root, "switch", 10).hits) == 0
    assert len(scan_project(root, "switch", 47).hits) == 1


def test_refuses_when_new_id_already_in_use(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    # add a second command using 47
    mapf = root / "data" / "Map001.json"
    d = json.loads(mapf.read_text())
    d["events"][1]["pages"][0]["list"].insert(0, {
        "code": 121, "indent": 0, "parameters": [47, 47, 0],
    })
    _write(mapf, d)
    with pytest.raises(ReassignError, match="already in use"):
        build_plan(root, "switch", 10, 47)


def test_refuses_same_old_and_new(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    with pytest.raises(ReassignError):
        build_plan(root, "switch", 10, 10)


def test_range_hit_warned_and_skipped(tmp_path):
    data = tmp_path / "data"
    _write(data / "Map001.json", {
        "events": [None, {"id": 1, "pages": [{"list": [
            {"code": 121, "indent": 0, "parameters": [8, 12, 0]},
            {"code": 0, "indent": 0, "parameters": []},
        ]}]}],
    })
    plan = build_plan(tmp_path, "switch", 10, 47)
    assert sum(len(v) for v in plan.patches_by_file.values()) == 0
    assert any("range" in w for w in plan.warnings)