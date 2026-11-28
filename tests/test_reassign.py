import json
from pathlib import Path

import pytest

from rpg_story_adjuster.apply import (
    build_plan, build_batch_plan, apply_plan, ReassignError,
)
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


def _proj_two_switches(tmp_path: Path, sw1: int, sw2: int) -> Path:
    data = tmp_path / "data"
    _write(data / "Map001.json", {
        "events": [None, {"id": 1, "pages": [{"list": [
            {"code": 121, "indent": 0, "parameters": [sw1, sw1, 0]},
            {"code": 121, "indent": 0, "parameters": [sw2, sw2, 0]},
            {"code": 0, "indent": 0, "parameters": []},
        ]}]}],
    })
    return tmp_path


# ---- Single (Phase 4-lite) ----

def test_dry_run_plan_lists_patches(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    plan = build_plan(root, "switch", 10, 47)
    assert sum(len(v) for v in plan.patches_by_file.values()) == 2
    assert plan.warnings == []


def test_apply_moves_id_and_verifies_post(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    before = scan_project(root, "switch", 10)
    assert len(before.hits) == 1
    plan = build_plan(root, "switch", 10, 47)
    apply_plan(root, plan, write_backups=False)
    assert len(scan_project(root, "switch", 10).hits) == 0
    assert len(scan_project(root, "switch", 47).hits) == 1


def test_refuses_when_new_id_already_in_use(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
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


def test_apply_creates_timestamped_backup(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    original = (root / "data" / "Map001.json").read_bytes()
    plan = build_plan(root, "switch", 10, 47)
    backup_dir = apply_plan(root, plan, write_backups=True)
    assert backup_dir is not None and backup_dir.exists()
    assert backup_dir.parent.name == ".rpgadj_backups"
    backed_up = (backup_dir / "data" / "Map001.json").read_bytes()
    assert backed_up == original
    patched = (root / "data" / "Map001.json").read_bytes()
    assert patched != backed_up
    assert b'"parameters":[47,47,0]' in patched


def test_apply_without_backups_still_works(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    plan = build_plan(root, "switch", 10, 47)
    result = apply_plan(root, plan, write_backups=False)
    assert result is None
    assert not (root / ".rpgadj_backups").exists()


# ---- Batch ----

def test_batch_swap_plan_and_apply(tmp_path):
    root = _proj_two_switches(tmp_path, 10, 47)
    plan = build_batch_plan(root, "switch", {10: 47, 47: 10})
    assert sum(len(v) for v in plan.patches_by_file.values()) == 4
    apply_plan(root, plan, write_backups=False)
    # After swap: both switches still in use, at each other's locations.
    assert len(scan_project(root, "switch", 10).hits) == 1
    assert len(scan_project(root, "switch", 47).hits) == 1
    parsed = json.loads((root / "data" / "Map001.json").read_bytes())
    p1 = parsed["events"][1]["pages"][0]["list"][0]["parameters"]
    p2 = parsed["events"][1]["pages"][0]["list"][1]["parameters"]
    assert p1 == [47, 47, 0]
    assert p2 == [10, 10, 0]


def test_batch_chain_plan_and_apply(tmp_path):
    root = _proj_two_switches(tmp_path, 10, 47)
    plan = build_batch_plan(root, "switch", {10: 47, 47: 100})
    apply_plan(root, plan, write_backups=False)
    assert len(scan_project(root, "switch", 10).hits) == 0
    assert len(scan_project(root, "switch", 47).hits) == 1
    assert len(scan_project(root, "switch", 100).hits) == 1


def test_batch_refuses_duplicate_target(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    with pytest.raises(ReassignError, match="duplicate target"):
        build_batch_plan(root, "switch", {10: 47, 20: 47})


def test_batch_refuses_target_in_use(tmp_path):
    root = _proj_two_switches(tmp_path, 10, 47)
    # 10 → 47 refused: 47 has hits, is not being vacated by the batch.
    with pytest.raises(ReassignError, match="already in use"):
        build_batch_plan(root, "switch", {10: 47})


def test_batch_refuses_self_mapping(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    with pytest.raises(ReassignError, match="old_id == new_id"):
        build_batch_plan(root, "switch", {10: 10})


def test_batch_empty_mapping_refused(tmp_path):
    root = _proj_with_switch(tmp_path, 10)
    with pytest.raises(ReassignError, match="empty"):
        build_batch_plan(root, "switch", {})