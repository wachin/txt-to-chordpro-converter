#!/usr/bin/env python3
"""
TXT to ChordPro Converter - PyQt6 GUI

Converts common church song text files with chords above lyrics and section
headers like [Verso], [Coro], [Intro] into valid ChordPro .cho files.
"""

import re
import sys
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QCoreApplication, QTranslator, QLocale, QLibraryInfo
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QMessageBox,
    QToolBar,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QCheckBox,
    QComboBox,
)

APP_NAME = "TXT to ChordPro Converter"
APP_VERSION = "1.0.0"
DEVELOPER = "Washington Indacochea Delgado"
DEVELOPER_EMAIL = "linuxfrontier@proton.me"
DEVELOPER_WEBSITE = "https://github.com/wachin/"


def tr(text, disambiguation=None):
    return QCoreApplication.translate("TxtToChordProApp", text, disambiguation)


def create_app_icon():
    icon_path = Path(__file__).parent / "assets" / "txt-to-chordpro.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


# -----------------------------------------------------------------------------
# Conversion logic
# -----------------------------------------------------------------------------

NOTE = r"(?:A|B|C|D|E|F|G|Do|Re|Mi|Fa|Sol|La|Si)"
ACC = r"(?:#|b)?"
QUALITY = r"(?:maj|min|m|sus|dim|aug|add|no|M|\+|-)?"
EXTRA = r"(?:[0-9]*(?:\([^)]*\))?(?:[#b]?[0-9]+)*(?:sus[24])?(?:add[0-9]+)?)?"
BASS = rf"(?:/{NOTE}{ACC})?"
CHORD_RE = re.compile(rf"^{NOTE}{ACC}{QUALITY}{EXTRA}{BASS}$")
SECTION_RE = re.compile(r"^\s*\[([^\[\]]+)\]\s*$")


def is_chord_token(token: str) -> bool:
    token = token.strip()
    if not token:
        return False
    # Avoid interpreting section names as chords.
    lower = token.lower()
    if lower in {"intro", "verso", "coro", "puente", "final", "instrumental", "pre-coro", "precoro"}:
        return False
    return bool(CHORD_RE.match(token))


def is_chord_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if SECTION_RE.match(stripped):
        return False
    tokens = stripped.split()
    if not tokens:
        return False
    return all(is_chord_token(tok) for tok in tokens)


def chord_positions(line: str):
    """Return [(column, chord), ...] for a chord-only line."""
    result = []
    for match in re.finditer(r"\S+", line):
        token = match.group(0)
        if is_chord_token(token):
            result.append((match.start(), token))
    return result


def merge_chords_with_lyrics(chord_line: str, lyric_line: str) -> str:
    """Insert [Chord] tokens into a lyric line according to chord columns."""
    result = lyric_line.rstrip("\n")
    for pos, chord in reversed(chord_positions(chord_line)):
        insert_at = min(pos, len(result))
        if pos > len(result):
            result = result + " " * (pos - len(result))
            insert_at = pos
        result = result[:insert_at] + f"[{chord}]" + result[insert_at:]
    return result.rstrip()


def chord_line_to_chordpro(line: str) -> str:
    return " ".join(f"[{chord}]" for _, chord in chord_positions(line))


def clean_title_key(title: str):
    """Extract key from titles like 'Song name (G)' and return (title_without_key, key)."""
    match = re.search(r"\s*\(([A-G](?:#|b)?)\)\s*$", title.strip())
    if match:
        key = match.group(1)
        clean_title = title[:match.start()].strip()
        return clean_title, key
    return title.strip(), None


def convert_text_to_chordpro(text: str) -> str:
    lines = text.splitlines()

    # Preserve first two meaningful lines as metadata.
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    title = lines[idx].strip() if idx < len(lines) else "Untitled"
    idx += 1

    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    artist = lines[idx].strip() if idx < len(lines) else ""
    idx += 1

    clean_title, key = clean_title_key(title)

    output = []
    output.append(f"{{title: {clean_title}}}")
    if artist:
        output.append(f"{{artist: {artist}}}")
    if key:
        output.append(f"{{key: {key}}}")

    body = lines[idx:]
    i = 0
    while i < len(body):
        line = body[i]
        stripped = line.strip()

        if not stripped:
            output.append("")
            i += 1
            continue

        section = SECTION_RE.match(stripped)
        if section:
            output.append(f"{{comment: {section.group(1).strip()}}}")
            i += 1
            continue

        # Also support unbracketed INTRO / FINAL lines commonly used in song sheets.
        if stripped.upper() in {"INTRO", "FINAL", "INSTRUMENTAL", "PUENTE"}:
            output.append(f"{{comment: {stripped.title()}}}")
            i += 1
            continue

        if is_chord_line(line):
            # If the next non-empty, non-section line is not a chord line, merge.
            if i + 1 < len(body):
                next_line = body[i + 1]
                next_stripped = next_line.strip()
                if next_stripped and not SECTION_RE.match(next_stripped) and not is_chord_line(next_line):
                    output.append(merge_chords_with_lyrics(line, next_line))
                    i += 2
                    continue
            output.append(chord_line_to_chordpro(line))
            i += 1
            continue

        output.append(line.rstrip())
        i += 1

    return "\n".join(output).rstrip() + "\n"


def convert_file(input_path: Path, output_extension: str = ".cho") -> Path:
    text = input_path.read_text(encoding="utf-8")
    converted = convert_text_to_chordpro(text)
    if not output_extension.startswith("."):
        output_extension = "." + output_extension
    output_path = input_path.with_suffix(output_extension)
    output_path.write_text(converted, encoding="utf-8", newline="\n")
    return output_path


# -----------------------------------------------------------------------------
# GUI widgets
# -----------------------------------------------------------------------------

class DropZoneWidget(QFrame):
    def __init__(self, on_upload_clicked, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False)
        self._build_ui(on_upload_clicked)

    def _build_ui(self, on_upload_clicked):
        self.setObjectName("dropZone")
        self.setStyleSheet("""
            QFrame#dropZone {
                border: 2px dashed #b0b8c1;
                border-radius: 10px;
                background-color: #fafafa;
            }
        """)
        self.setMinimumHeight(130)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self.lbl_drag = QLabel(tr("Drag and drop TXT song files"))
        self.lbl_drag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drag.setStyleSheet("font-size: 15px; font-weight: bold; color: #222; border: none;")

        self.lbl_or = QLabel(tr("or"))
        self.lbl_or.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_or.setStyleSheet("font-size: 13px; color: #666; border: none;")

        self.btn_upload = QPushButton(tr("⬆  Add files"))
        self.btn_upload.setFixedSize(150, 36)
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2bbfa4, stop:1 #1a9e87);
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover { background: #158a74; }
            QPushButton:pressed { background: #117a63; }
        """)
        self.btn_upload.clicked.connect(on_upload_clicked)

        layout.addWidget(self.lbl_drag)
        layout.addWidget(self.lbl_or)
        layout.addWidget(self.btn_upload, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)


class TxtToChordProApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.qt_translator = QTranslator()
        self._load_qt_translation()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(create_app_icon())
        self.resize(760, 520)
        self.setAcceptDrops(True)
        self.files = []
        self.init_ui()
        self.center_window()

    def center_window(self):
        frame = self.frameGeometry()
        screen = QApplication.primaryScreen()
        center = screen.availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())

    def _load_qt_translation(self):
        translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        locale_name = QLocale.system().name()
        locale_short = locale_name.split("_")[0]
        for name in [f"qtbase_{locale_name}", f"qtbase_{locale_short}"]:
            if self.qt_translator.load(name, translations_path):
                QApplication.installTranslator(self.qt_translator)
                return

    def init_ui(self):
        toolbar = QToolBar(tr("Main toolbar"))
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        btn_about = QPushButton(tr("About..."))
        btn_about.clicked.connect(self.show_about)
        toolbar.addWidget(btn_about)

        central = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.drop_zone = DropZoneWidget(self.open_file_dialog)
        layout.addWidget(self.drop_zone)

        top_row = QHBoxLayout()
        self.count_label = QLabel(tr("Added files: 0"))
        self.count_label.setStyleSheet("font-weight: bold;")
        top_row.addWidget(self.count_label)
        top_row.addStretch()

        top_row.addWidget(QLabel(tr("Output format:")))
        self.extension_combo = QComboBox()
        self.extension_combo.addItems([".cho", ".chopro"])
        top_row.addWidget(self.extension_combo)
        layout.addLayout(top_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([tr("Convert"), tr("File"), tr("Folder")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        self.btn_select_all = QPushButton(tr("Select all"))
        self.btn_select_all.clicked.connect(self.select_all)
        button_row.addWidget(self.btn_select_all)

        self.btn_unselect_all = QPushButton(tr("Unselect all"))
        self.btn_unselect_all.clicked.connect(self.unselect_all)
        button_row.addWidget(self.btn_unselect_all)

        self.btn_clear = QPushButton(tr("Clear list"))
        self.btn_clear.clicked.connect(self.clear_list)
        button_row.addWidget(self.btn_clear)

        button_row.addStretch()

        self.btn_convert = QPushButton(tr("Convert selected files"))
        self.btn_convert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convert.setStyleSheet("""
            QPushButton {
                background-color: #1a9e87;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 9px 18px;
            }
            QPushButton:hover { background-color: #158a74; }
            QPushButton:pressed { background-color: #117a63; }
        """)
        self.btn_convert.clicked.connect(self.convert_selected)
        button_row.addWidget(self.btn_convert)
        layout.addLayout(button_row)

        self.result_label = QLabel(tr("Add .txt files to convert them to valid ChordPro."))
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def show_about(self):
        text = (
            f"<b>{APP_NAME}</b> {APP_VERSION}<br><br>"
            f"<b>{tr('Developer')}:</b> {DEVELOPER}<br>"
            f"<b>{tr('Email')}:</b> {DEVELOPER_EMAIL}<br>"
            f"<b>{tr('Website')}:</b> <a href='{DEVELOPER_WEBSITE}'>{DEVELOPER_WEBSITE}</a><br><br>"
            f"<b>{tr('What it does')}:</b><br>"
            "Converts TXT song sheets with chords above lyrics and [sections] into valid ChordPro files.<br><br>"
            f"<b>{tr('Technologies used')}:</b><br>Python 3<br>PyQt6<br>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("About"))
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def open_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Select TXT song files"),
            "",
            tr("Text files (*.txt);;All files (*)"),
            options=QFileDialog.Option(0),
        )
        if file_paths:
            self.add_files(file_paths)

    def add_files(self, paths):
        added = 0
        existing = {str(p) for p in self.files}
        for raw in paths:
            path = Path(raw)
            if not path.exists() or not path.is_file():
                continue
            if path.suffix.lower() != ".txt":
                continue
            if str(path) in existing:
                continue
            self.files.append(path)
            existing.add(str(path))
            added += 1
            row = self.table.rowCount()
            self.table.insertRow(row)

            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox.setStyleSheet("margin-left: 14px;")
            self.table.setCellWidget(row, 0, checkbox)

            self.table.setItem(row, 1, QTableWidgetItem(path.name))
            self.table.setItem(row, 2, QTableWidgetItem(str(path.parent)))

        self.update_count()
        if added:
            self.result_label.setText(tr("Files added and marked for conversion."))
        else:
            self.result_label.setText(tr("No new TXT files were added."))

    def update_count(self):
        self.count_label.setText(tr("Added files:") + f" {len(self.files)}")

    def select_all(self):
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def unselect_all(self):
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def clear_list(self):
        self.files.clear()
        self.table.setRowCount(0)
        self.update_count()
        self.result_label.setText(tr("List cleared."))

    def convert_selected(self):
        if not self.files:
            QMessageBox.warning(self, tr("No files"), tr("Please add TXT files first."))
            return

        selected = []
        for row, path in enumerate(self.files):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selected.append(path)

        if not selected:
            QMessageBox.warning(self, tr("No selected files"), tr("Please select at least one file to convert."))
            return

        extension = self.extension_combo.currentText()
        converted = []
        errors = []
        for path in selected:
            try:
                output_path = convert_file(path, extension)
                converted.append(output_path)
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")

        if errors:
            QMessageBox.warning(
                self,
                tr("Finished with errors"),
                tr("Some files could not be converted:") + "\n\n" + "\n".join(errors),
            )

        if converted:
            self.result_label.setText(
                tr("Converted files:") + f" {len(converted)}\n" + "\n".join(str(p) for p in converted[:6])
            )
            QMessageBox.information(
                self,
                tr("Done"),
                tr("Files converted successfully:") + f" {len(converted)}",
            )

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_files(paths)
            event.acceptProposedAction()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(create_app_icon())
    window = TxtToChordProApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
