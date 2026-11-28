from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    root: Path

    def data_dir(self) -> Path:
        return self.root / "data"

    def list_data_files(self) -> list[Path]:
        return sorted(self.data_dir().glob("*.json"))
