from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LoadedJson:
    path: Path
    raw_bytes: bytes
    data: dict | list
    edited: bool = False

    def write_back(self, out_path: Path | None = None) -> None:
        target = out_path or self.path
        if not self.edited:
            # Phase 0 exit criterion: unchanged file -> byte-identical write.
            target.write_bytes(self.raw_bytes)
            return
        # Phase 3 territory. Strategy (canonical vs surgical) depends on the
        # probe output. Deliberately disabled until round-trip tests exist.
        raise NotImplementedError(
            "Editing write path disabled until Phase 3 round-trip tests pass. "
            "Phase 0 only supports byte-exact pass-through of unedited files."
        )


def load_json(path: Path) -> LoadedJson:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    return LoadedJson(path=path, raw_bytes=raw, data=data)
