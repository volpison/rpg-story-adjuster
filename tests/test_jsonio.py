import json
from pathlib import Path

from rpg_story_adjuster.jsonio import load_json


def test_pass_through_is_byte_identical(tmp_path: Path):
    src = tmp_path / "Map001.json"
    payload = {"data": [None, {"code": 101, "indent": 0, "parameters": ["hi"]}]}
    src.write_text(json.dumps(payload, separators=(",", ":")))

    loaded = load_json(src)
    out = tmp_path / "copy.json"
    loaded.write_back(out)

    assert out.read_bytes() == src.read_bytes()
