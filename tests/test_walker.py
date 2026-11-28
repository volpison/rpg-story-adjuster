from pathlib import Path

from rpg_story_adjuster.jsonio import load_json
from rpg_story_adjuster.walker import (
    iter_common_event_commands,
    iter_map_commands,
    iter_project_commands,
    iter_troop_commands,
)


def _fingerprint(cmds):
    return [(c.source.file, c.source.event_id, c.source.page_index,
             c.source.command_index, c.code, c.indent, c.parameters)
            for c in cmds]


def test_map_walker_yields_events_pages_in_order(tiny_project: Path):
    cmds = list(iter_map_commands(tiny_project / "data" / "Map001.json",
                                  tiny_project))
    fp = _fingerprint(cmds)
    assert fp[0] == ("data/Map001.json", 1, 0, 0, 101, 0, ["Hello"])
    assert fp[1] == ("data/Map001.json", 1, 0, 1, 121, 0, [10, 10, 0])
    assert fp[2] == ("data/Map001.json", 1, 0, 2, 0,   0, [])
    assert fp[3] == ("data/Map001.json", 1, 1, 0, 111, 0, [0, 10, 1])
    # event 2 contributes exactly one (terminator) command
    assert fp[-1] == ("data/Map001.json", 2, 0, 0, 0, 0, [])
    assert len(cmds) == 7


def test_common_event_walker_skips_null_zero(tiny_project: Path):
    cmds = list(iter_common_event_commands(
        tiny_project / "data" / "CommonEvents.json", tiny_project))
    assert len(cmds) == 2
    assert cmds[0].source == cmds[0].source.__class__(
        file="data/CommonEvents.json", event_id=1,
        page_index=None, command_index=0,
        json_path=(1, "list", 0))
    assert cmds[0].code == 122


def test_troop_walker(tiny_project: Path):
    cmds = list(iter_troop_commands(
        tiny_project / "data" / "Troops.json", tiny_project))
    assert [c.code for c in cmds] == [121, 0]


def test_project_walker_covers_all_three_files(tiny_project: Path):
    files = {c.source.file for c in iter_project_commands(tiny_project)}
    assert files == {
        "data/Map001.json",
        "data/CommonEvents.json",
        "data/Troops.json",
    }


def test_malformed_entries_are_skipped(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "Map001.json").write_text(
        '{"events":[null,{"id":1,"pages":[{"list":[null,'
        '{"code":"not an int"},{"code":0,"indent":0,"parameters":"bad"},'
        '{"code":0,"indent":0,"parameters":[]}]}]}]}',
        encoding="utf-8",
    )
    cmds = list(iter_map_commands(data / "Map001.json", tmp_path))
    assert len(cmds) == 2                 # bad code dropped, bad params coerced
    assert cmds[0].parameters == []       # non-list parameters -> []
    assert cmds[1].code == 0


def test_round_trip_leaves_file_byte_identical(tiny_project: Path):
    for name in ("Map001.json", "CommonEvents.json", "Troops.json"):
        p = tiny_project / "data" / name
        before = p.read_bytes()
        loaded = load_json(p)
        loaded.write_back()
        assert p.read_bytes() == before
