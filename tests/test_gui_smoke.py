"""Smoke tests for the GUI shell. Skipped if PySide6 isn't installed."""
import pytest

pytest.importorskip("PySide6")


def test_main_window_module_imports():
    import rpg_story_adjuster.gui.main_window  # noqa: F401


def test_worker_classes_exist():
    from rpg_story_adjuster.gui.main_window import (
        _ApplyWorker, _PlanWorker, _ScanWorker,
    )
    assert _ScanWorker is not None
    assert _PlanWorker is not None
    assert _ApplyWorker is not None