"""GUI shell. All logic lives in the library modules (scan, apply, printer,
walker, jsonio_surgical). This file only orchestrates.
"""
from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSpinBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from rpg_story_adjuster.apply import (
    apply_plan, build_plan, build_batch_plan, parse_mapping_str,
    ReassignError, ReassignPlan,
)
from rpg_story_adjuster.printer import print_project
from rpg_story_adjuster.scan import scan_project, ScanResult


class _ScanWorker(QThread):
    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(self, root: Path, kind: str, id_: int) -> None:
        super().__init__()
        self._root = root
        self._kind = kind
        self._id = id_

    def run(self) -> None:
        try:
            self.finished_result.emit(scan_project(self._root, self._kind, self._id))
        except Exception as e:
            self.failed.emit(str(e))


class _PlanWorker(QThread):
    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(self, root: Path, kind: str,
                 mapping: dict[int, int] | None = None,
                 single: tuple[int, int] | None = None) -> None:
        super().__init__()
        self._root = root
        self._kind = kind
        self._mapping = mapping
        self._single = single

    def run(self) -> None:
        try:
            if self._mapping is not None:
                plan = build_batch_plan(self._root, self._kind, self._mapping)
            else:
                assert self._single is not None
                plan = build_plan(self._root, self._kind, self._single[0], self._single[1])
            self.finished_result.emit(plan)
        except ReassignError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f"unexpected: {e}")


class _ApplyWorker(QThread):
    finished_result = Signal(object)
    failed = Signal(str)

    def __init__(self, root: Path, plan: ReassignPlan) -> None:
        super().__init__()
        self._root = root
        self._plan = plan

    def run(self) -> None:
        try:
            self.finished_result.emit(apply_plan(self._root, self._plan))
        except Exception as e:
            self.failed.emit(str(e))


class _RenderWorker(QThread):
    finished_result = Signal(str)
    failed = Signal(str)

    def __init__(self, root: Path, file_filter: str | None,
                 event_filter: int | None, page_filter: int | None) -> None:
        super().__init__()
        self._root = root
        self._file = file_filter
        self._event = event_filter
        self._page = page_filter

    def run(self) -> None:
        try:
            text = print_project(
                self._root,
                file=self._file, event=self._event, page=self._page,
            )
            self.finished_result.emit(text)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RPG Story Adjuster")
        self.resize(1200, 750)

        self._project_root: Path | None = None
        self._plan: ReassignPlan | None = None
        self._worker: QThread | None = None

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.addLayout(self._build_project_row())

        tabs = QTabWidget()
        tabs.addTab(self._build_scan_tab(), "Scan")
        tabs.addTab(self._build_reassign_tab(), "Reassign")
        tabs.addTab(self._build_print_tab(), "Print")
        outer.addWidget(tabs, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Open a project to begin.")

    def _build_project_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self._project_label = QLabel("No project loaded")
        btn = QPushButton("Open project…")
        btn.clicked.connect(self._on_open_project)
        row.addWidget(QLabel("Project:"))
        row.addWidget(self._project_label, 1)
        row.addWidget(btn)
        return row

    def _build_scan_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        controls = QHBoxLayout()
        self._scan_kind = QComboBox()
        self._scan_kind.addItems(["switch", "variable"])
        self._scan_id = QSpinBox()
        self._scan_id.setRange(1, 9999)
        self._scan_id.setValue(1)
        self._scan_dynamic = QCheckBox("Show dynamic refs")
        self._scan_btn = QPushButton("Scan")
        self._scan_btn.clicked.connect(self._on_scan)

        controls.addWidget(QLabel("Kind:"))
        controls.addWidget(self._scan_kind)
        controls.addWidget(QLabel("ID:"))
        controls.addWidget(self._scan_id)
        controls.addWidget(self._scan_dynamic)
        controls.addWidget(self._scan_btn)
        controls.addStretch(1)
        v.addLayout(controls)

        self._scan_tree = QTreeWidget()
        self._scan_tree.setHeaderLabels(
            ["File", "Event", "Page", "Command", "Via", "Detail"]
        )
        self._scan_tree.setColumnWidth(0, 260)
        v.addWidget(self._scan_tree, 1)
        return w

    def _build_reassign_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        controls = QHBoxLayout()
        self._rr_kind = QComboBox()
        self._rr_kind.addItems(["switch", "variable"])
        self._rr_batch_cb = QCheckBox("Batch")
        self._rr_batch_cb.toggled.connect(self._on_batch_toggle)

        self._rr_old_label = QLabel("Old:")
        self._rr_old = QSpinBox(); self._rr_old.setRange(1, 9999); self._rr_old.setValue(1)
        self._rr_new_label = QLabel("New:")
        self._rr_new = QSpinBox(); self._rr_new.setRange(1, 9999); self._rr_new.setValue(2)

        self._rr_map_label = QLabel("Map:")
        self._rr_map = QLineEdit()
        self._rr_map.setPlaceholderText("10:47,20:30")
        self._rr_map.setMinimumWidth(220)
        self._rr_map.setVisible(False)
        self._rr_map_label.setVisible(False)

        self._rr_dry_btn = QPushButton("Dry run")
        self._rr_dry_btn.clicked.connect(self._on_dry_run)
        self._rr_apply_btn = QPushButton("Apply")
        self._rr_apply_btn.setEnabled(False)
        self._rr_apply_btn.clicked.connect(self._on_apply)

        controls.addWidget(QLabel("Kind:"))
        controls.addWidget(self._rr_kind)
        controls.addWidget(self._rr_batch_cb)
        controls.addWidget(self._rr_old_label)
        controls.addWidget(self._rr_old)
        controls.addWidget(self._rr_new_label)
        controls.addWidget(self._rr_new)
        controls.addWidget(self._rr_map_label)
        controls.addWidget(self._rr_map)
        controls.addWidget(self._rr_dry_btn)
        controls.addWidget(self._rr_apply_btn)
        controls.addStretch(1)
        v.addLayout(controls)

        self._plan_tree = QTreeWidget()
        self._plan_tree.setHeaderLabels(["File", "Path", "Change"])
        self._plan_tree.setColumnWidth(0, 260)
        v.addWidget(self._plan_tree, 1)

        v.addWidget(QLabel("Warnings:"))
        self._warnings = QPlainTextEdit()
        self._warnings.setReadOnly(True)
        self._warnings.setMaximumHeight(120)
        v.addWidget(self._warnings)
        return w

    def _build_print_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        controls = QHBoxLayout()
        self._pr_file = QLineEdit()
        self._pr_file.setPlaceholderText("Map001.json (leave empty for all)")
        self._pr_file.setMinimumWidth(200)
        self._pr_event = QLineEdit()
        self._pr_event.setPlaceholderText("event id (leave empty for all)")
        self._pr_event.setMaximumWidth(180)
        self._pr_page = QLineEdit()
        self._pr_page.setPlaceholderText("page (leave empty for all)")
        self._pr_page.setMaximumWidth(160)
        self._pr_render_btn = QPushButton("Render")
        self._pr_render_btn.clicked.connect(self._on_print)

        controls.addWidget(QLabel("File:"))
        controls.addWidget(self._pr_file)
        controls.addWidget(QLabel("Event:"))
        controls.addWidget(self._pr_event)
        controls.addWidget(QLabel("Page:"))
        controls.addWidget(self._pr_page)
        controls.addWidget(self._pr_render_btn)
        controls.addStretch(1)
        v.addLayout(controls)

        self._pr_output = QPlainTextEdit()
        self._pr_output.setReadOnly(True)
        self._pr_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        v.addWidget(self._pr_output, 1)
        return w

    def load_project(self, root: Path) -> bool:
        if not (root / "data").is_dir():
            return False
        self._project_root = root
        self._plan = None
        self._rr_apply_btn.setEnabled(False)
        self._plan_tree.clear()
        self._warnings.clear()
        self._scan_tree.clear()
        self._pr_output.clear()
        self._project_label.setText(str(root))
        self.statusBar().showMessage(f"Loaded: {root}")
        return True

    def _on_open_project(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select RPG Maker MZ project folder")
        if not d:
            return
        if not self.load_project(Path(d)):
            QMessageBox.warning(self, "Not a project",
                                f"No data/ subfolder under:\n{d}")

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _on_scan(self) -> None:
        if not self._project_root:
            QMessageBox.warning(self, "No project", "Open a project first.")
            return
        if self._busy():
            return
        kind = self._scan_kind.currentText()
        id_ = self._scan_id.value()
        self._scan_tree.clear()
        self._scan_btn.setEnabled(False)
        self.statusBar().showMessage(f"Scanning for {kind} {id_}…")
        self._worker = _ScanWorker(self._project_root, kind, id_)
        self._worker.finished_result.connect(self._on_scan_done)
        self._worker.failed.connect(self._on_scan_failed)
        self._worker.start()

    def _on_scan_done(self, result: ScanResult) -> None:
        self._scan_btn.setEnabled(True)
        for h in result.hits:
            s = h.source
            QTreeWidgetItem(self._scan_tree, [
                s.file, _fmt(s.event_id), _fmt(s.page_index),
                _fmt(s.command_index), h.via, h.detail or "",
            ])
        if self._scan_dynamic.isChecked():
            grey = QColor("#888")
            for d in result.dynamic:
                s = d.source
                item = QTreeWidgetItem(self._scan_tree, [
                    s.file, _fmt(s.event_id), _fmt(s.page_index),
                    _fmt(s.command_index), f"dynamic ({d.via})", d.snippet,
                ])
                for col in range(item.columnCount()):
                    item.setForeground(col, grey)
        self.statusBar().showMessage(
            f"{len(result.hits)} hit(s)"
            + (f", {len(result.dynamic)} dynamic" if result.dynamic else "")
        )

    def _on_scan_failed(self, msg: str) -> None:
        self._scan_btn.setEnabled(True)
        QMessageBox.critical(self, "Scan failed", msg)
        self.statusBar().showMessage("Scan failed")

    def _on_batch_toggle(self, checked: bool) -> None:
        self._rr_old_label.setVisible(not checked)
        self._rr_old.setVisible(not checked)
        self._rr_new_label.setVisible(not checked)
        self._rr_new.setVisible(not checked)
        self._rr_map_label.setVisible(checked)
        self._rr_map.setVisible(checked)

    def _on_dry_run(self) -> None:
        if not self._project_root:
            QMessageBox.warning(self, "No project", "Open a project first.")
            return
        if self._busy():
            return
        kind = self._rr_kind.currentText()
        self._plan_tree.clear()
        self._warnings.clear()
        self._plan = None
        self._rr_apply_btn.setEnabled(False)
        self._rr_dry_btn.setEnabled(False)

        if self._rr_batch_cb.isChecked():
            text = self._rr_map.text().strip()
            try:
                mapping = parse_mapping_str(text)
            except ReassignError as e:
                self._rr_dry_btn.setEnabled(True)
                QMessageBox.warning(self, "Invalid mapping", str(e))
                return
            self.statusBar().showMessage(f"Building batch plan ({len(mapping)} pairs)…")
            self._worker = _PlanWorker(self._project_root, kind, mapping=mapping)
        else:
            old, new = self._rr_old.value(), self._rr_new.value()
            self.statusBar().showMessage(f"Building plan: {kind} {old} → {new}…")
            self._worker = _PlanWorker(self._project_root, kind, single=(old, new))

        self._worker.finished_result.connect(self._on_plan_done)
        self._worker.failed.connect(self._on_plan_failed)
        self._worker.start()

    def _on_plan_done(self, plan: ReassignPlan) -> None:
        self._rr_dry_btn.setEnabled(True)
        self._plan = plan
        total = sum(len(v) for v in plan.patches_by_file.values())
        for rel_file, patches in sorted(plan.patches_by_file.items()):
            for path, o, n in patches:
                QTreeWidgetItem(self._plan_tree, [rel_file, str(path), f"{o} → {n}"])
        for w in plan.warnings:
            self._warnings.appendPlainText(w)
        if total > 0:
            self._rr_apply_btn.setEnabled(True)
            self.statusBar().showMessage(
                f"Plan ready: {total} patch(es) in {len(plan.patches_by_file)} file(s)."
            )
        else:
            self.statusBar().showMessage("Plan empty — nothing to apply.")

    def _on_plan_failed(self, msg: str) -> None:
        self._rr_dry_btn.setEnabled(True)
        QMessageBox.warning(self, "Dry run refused", msg)
        self.statusBar().showMessage("Dry run refused")

    def _on_apply(self) -> None:
        if not self._plan or not self._project_root:
            return
        if self._busy():
            return
        total = sum(len(v) for v in self._plan.patches_by_file.values())
        reply = QMessageBox.question(
            self, "Confirm apply",
            f"Write {total} patch(es) to {len(self._plan.patches_by_file)} file(s)?\n\n"
            "A backup folder will be created under <project>/.rpgadj_backups/.",
        )
        if reply != QMessageBox.Yes:
            return
        self._rr_apply_btn.setEnabled(False)
        self._rr_dry_btn.setEnabled(False)
        self.statusBar().showMessage("Applying…")
        self._worker = _ApplyWorker(self._project_root, self._plan)
        self._worker.finished_result.connect(self._on_apply_done)
        self._worker.failed.connect(self._on_apply_failed)
        self._worker.start()

    def _on_apply_done(self, backup_dir) -> None:
        self._rr_dry_btn.setEnabled(True)
        msg = "Applied. Post-scan invariant verified."
        if backup_dir:
            msg += f"\n\nBackup folder:\n{backup_dir}"
        QMessageBox.information(self, "Apply complete", msg)
        self._plan = None
        self._rr_apply_btn.setEnabled(False)
        self.statusBar().showMessage("Apply complete")

    def _on_apply_failed(self, msg: str) -> None:
        self._rr_dry_btn.setEnabled(True)
        QMessageBox.critical(self, "Apply failed", msg)
        self.statusBar().showMessage("Apply failed")

    def _on_print(self) -> None:
        if not self._project_root:
            QMessageBox.warning(self, "No project", "Open a project first.")
            return
        if self._busy():
            return
        file_filter = self._pr_file.text().strip() or None
        try:
            event_filter = int(self._pr_event.text().strip()) if self._pr_event.text().strip() else None
        except ValueError:
            QMessageBox.warning(self, "Invalid event", "Event ID must be an integer.")
            return
        try:
            page_filter = int(self._pr_page.text().strip()) if self._pr_page.text().strip() else None
        except ValueError:
            QMessageBox.warning(self, "Invalid page", "Page must be an integer.")
            return
        self._pr_render_btn.setEnabled(False)
        self.statusBar().showMessage("Rendering…")
        self._worker = _RenderWorker(
            self._project_root, file_filter, event_filter, page_filter,
        )
        self._worker.finished_result.connect(self._on_print_done)
        self._worker.failed.connect(self._on_print_failed)
        self._worker.start()

    def _on_print_done(self, text: str) -> None:
        self._pr_render_btn.setEnabled(True)
        self._pr_output.setPlainText(text)
        lines = text.count("\n")
        self.statusBar().showMessage(f"Rendered {lines} line(s).")

    def _on_print_failed(self, msg: str) -> None:
        self._pr_render_btn.setEnabled(True)
        QMessageBox.critical(self, "Render failed", msg)
        self.statusBar().showMessage("Render failed")


def _fmt(v) -> str:
    return "—" if v is None else str(v)


def run(project_root: Path | None = None) -> int:
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    if project_root is not None:
        if not w.load_project(project_root):
            print(f"not a project (no data/): {project_root}", file=sys.stderr)
            return 1
    w.show()
    return app.exec()