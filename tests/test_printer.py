import json
from pathlib import Path

import pytest

from rpg_story_adjuster.printer import print_project


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, separators=(",", ":")),
        encoding="utf-8",
    )


@pytest.fixture
def printer_project(tmp_path: Path) -> Path:
    _write(tmp_path / "data" / "Map001.json", {
        "events": [None, {"id": 1, "pages": [{"list": [
            {"code": 101, "indent": 0, "parameters": ["Main", 0, 0, 2, "Joyanne"]},
            {"code": 401, "indent": 0, "parameters": ["Hello"]},
            {"code": 401, "indent": 0, "parameters": ["World"]},
            {"code": 121, "indent": 0, "parameters": [10, 10, 0]},
            {"code": 121, "indent": 0, "parameters": [5, 8, 1]},
            {"code": 122, "indent": 0, "parameters": [4, 4, 0, 3, 0]},
            {"code": 122, "indent": 0, "parameters": [4, 4, 1, 10, 1]},
            {"code": 111, "indent": 0, "parameters": [0, 28, 0]},
            {"code": 121, "indent": 1, "parameters": [6, 6, 0]},
            {"code": 0,   "indent": 1, "parameters": []},
            {"code": 412, "indent": 0, "parameters": []},
            {"code": 0,   "indent": 0, "parameters": []},
            {"code": 108, "indent": 0, "parameters": ["This is a comment"]},
            {"code": 117, "indent": 0, "parameters": [5]},
            {"code": 118, "indent": 0, "parameters": ["my_label"]},
            {"code": 119, "indent": 0, "parameters": ["my_label"]},
            {"code": 355, "indent": 0, "parameters": ["var x = 1;"]},
            {"code": 655, "indent": 0, "parameters": ["var y = 2;"]},
            {"code": 999, "indent": 0, "parameters": [{"weird": True}]},
            {"code": 0,   "indent": 0, "parameters": []},
        ]}]}],
    })
    return tmp_path


EXPECTED = (
    "# data/Map001.json · event 1 · page 0\n"
    '◆ 101  face=Main[0] bg=window pos=bottom name="Joyanne"\n'
    '◆ 401  "Hello"\n'
    '◆ 401  "World"\n'
    '◆ 121  Switches[10] = ON\n'
    '◆ 121  Switches[5..8] = OFF\n'
    '◆ 122  Variable[4] = 3\n'
    '◆ 122  Variable[4] += Variable[10]\n'
    '◆ 111  Switch[28] is ON\n'
    '  ◆ 121  Switches[6] = ON\n'
    '  ◆ 0\n'
    '◆ 412  Else\n'
    '◆ 0\n'
    '◆ 108  "This is a comment"\n'
    '◆ 117  Common Event[5]\n'
    '◆ 118  Label "my_label"\n'
    '◆ 119  Jump "my_label"\n'
    '◆ 355  "var x = 1;"\n'
    '◆ 655  "var y = 2;"\n'
    "◆ 999  [raw] [{'weird': True}]\n"
    '◆ 0\n'
)


def test_printer_golden_fixture(printer_project: Path):
    assert print_project(printer_project) == EXPECTED


def test_printer_deterministic(printer_project: Path):
    a = print_project(printer_project)
    b = print_project(printer_project)
    assert a == b


def test_printer_tiny_project(tiny_project: Path):
    out = print_project(tiny_project)
    expected = (
        "# data/Map001.json · event 1 · page 0\n"
        "◆ 101  [raw] ['Hello']\n"
        "◆ 121  Switches[10] = ON\n"
        "◆ 0\n"
        "\n"
        "# data/Map001.json · event 1 · page 1\n"
        "◆ 111  Switch[10] is OFF\n"
        "◆ 0\n"
        "  ◆ 0\n"
        "\n"
        "# data/Map001.json · event 2 · page 0\n"
        "◆ 0\n"
        "\n"
        "# data/CommonEvents.json · event 1\n"
        "◆ 122  Variable[5] = Variable[3]\n"
        "◆ 0\n"
        "\n"
        "# data/Troops.json · event 1 · page 0\n"
        "◆ 121  Switches[20] = OFF\n"
        "◆ 0\n"
    )
    assert out == expected


def test_printer_filter_by_file(printer_project: Path):
    out = print_project(printer_project, file="Map001.json")
    assert out == EXPECTED
    # Filtering to a file that doesn't exist yields empty output.
    assert print_project(printer_project, file="Map999.json") == "\n"


def test_printer_filter_by_event(printer_project: Path):
    out = print_project(printer_project, event=1)
    assert out == EXPECTED
    assert print_project(printer_project, event=2) == "\n"


def test_printer_filter_by_page(printer_project: Path):
    out = print_project(printer_project, page=0)
    assert out == EXPECTED
    assert print_project(printer_project, page=1) == "\n"