from __future__ import annotations
import sys


def run() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
    except ImportError:
        print("GUI requires PySide6: pip install -e '.[gui]'", file=sys.stderr)
        return 1

    app = QApplication.instance() or QApplication(sys.argv)
    w = QMainWindow()
    w.setWindowTitle("RPG Story Adjuster")
    w.setCentralWidget(QLabel(
        "Phase 0 shell.\n\n"
        "CLI:  python main.py list-files <project>"
    ))
    w.resize(640, 400)
    w.show()
    return app.exec()
