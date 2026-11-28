from rpg_story_adjuster.apply import apply_reassign_to_commands
from rpg_story_adjuster.scan import scan_commands
from rpg_story_adjuster.walker import iter_project_commands


def test_switch_reassign_preserves_scan_invariant(tiny_project):
    cmds = list(iter_project_commands(tiny_project))
    before_10 = scan_commands(cmds, "switch", 10)
    before_47 = scan_commands(cmds, "switch", 47)
    assert len(before_10.hits) == 2
    assert len(before_47.hits) == 0

    r = apply_reassign_to_commands(cmds, "switch", 10, 47)
    assert r.rewritten == 2

    after_10 = scan_commands(cmds, "switch", 10)
    after_47 = scan_commands(cmds, "switch", 47)
    # Roadmap principle #9: old ID has zero hits; new ID has exactly the old
    # hits plus whatever 47 had before.
    assert len(after_10.hits) == 0
    assert len(after_47.hits) == len(before_10.hits) + len(before_47.hits)


def test_range_skip_does_not_break_invariant(tmp_path):
    import json
    from pathlib import Path
    data = tmp_path / "data"
    data.mkdir()
    (data / "Map001.json").write_text(json.dumps({
        "events": [None, {"id": 1, "pages": [{"list": [
            {"code": 121, "indent": 0, "parameters": [8, 12, 0]},
            {"code": 0, "indent": 0, "parameters": []},
        ]}]}],
    }, separators=(",", ":")))
    cmds = list(iter_project_commands(tmp_path))
    assert len(scan_commands(cmds, "switch", 10).hits) == 1

    r = apply_reassign_to_commands(cmds, "switch", 10, 47)
    assert r.rewritten == 0
    assert r.skipped_ranges == 1

    # Old ID still hits (range covers it); new ID does not.
    assert len(scan_commands(cmds, "switch", 10).hits) == 1
    assert len(scan_commands(cmds, "switch", 47).hits) == 0
