import json
from pathlib import Path

import pytest


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )


@pytest.fixture
def tiny_project(tmp_path: Path) -> Path:
    data = tmp_path / "data"

    _write(data / "Map001.json", {
        "displayName": "Map001",
        "events": [
            None,
            {
                "id": 1, "name": "EV001",
                "pages": [
                    {"list": [
                        {"code": 101, "indent": 0, "parameters": ["Hello"]},
                        {"code": 121, "indent": 0, "parameters": [10, 10, 0]},
                        {"code": 0,   "indent": 0, "parameters": []},
                    ]},
                    {"list": [
                        {"code": 111, "indent": 0, "parameters": [0, 10, 1]},
                        {"code": 0,   "indent": 0, "parameters": []},
                        {"code": 0,   "indent": 1, "parameters": []},
                    ]},
                ],
            },
            {
                "id": 2, "name": "EV002",
                "pages": [
                    {"list": [
                        {"code": 0, "indent": 0, "parameters": []},
                    ]},
                ],
            },
        ],
    })

    _write(data / "CommonEvents.json", [
        None,
        {
            "id": 1, "name": "CE001",
            "list": [
                {"code": 122, "indent": 0, "parameters": [5, 5, 0, 3, 1]},
                {"code": 0,   "indent": 0, "parameters": []},
            ],
        },
    ])

    _write(data / "Troops.json", [
        None,
        {
            "id": 1, "name": "Troop1",
            "pages": [
                {"list": [
                    {"code": 121, "indent": 0, "parameters": [20, 20, 1]},
                    {"code": 0,   "indent": 0, "parameters": []},
                ]},
            ],
        },
    ])

    return tmp_path
