import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import psutil
from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtGui import QFont, QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QVBoxLayout, QWidget, QDialog, QDialogButtonBox, QTableWidget,
    QTableWidgetItem, QTabWidget
)

from curriculum import available_curricula, get_curriculum, subjects_for, stages_for

APP_NAME = "StudyLock"
DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "StudyLock"
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUESTIONS_FILE = DATA_DIR / "questions.json"
STATS_FILE = DATA_DIR / "stats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_QUESTIONS = {
    "Chemistry": [
        {
            "question": "What is the charge of a proton?",
            "answers": ["+1", "positive one", "1"],
            "topic": "Atomic structure",
            "difficulty": "Normal",
            "curriculum": "gcse",
            "subject": "Chemistry",
            "qualification_stage": "O Level",
            "exam_board": "Sample",
            "paper_reference": "Sample question",
        },
        {
            "question": "What is the chemical symbol for sodium?",
            "answers": ["Na"],
            "topic": "Atomic structure",
            "difficulty": "Easy",
            "curriculum": "gcse",
            "subject": "Chemistry",
            "qualification_stage": "O Level",
            "exam_board": "Sample",
            "paper_reference": "Sample question",
        },
    ]
}


def normalize(text: str) -> str:
    text = str(text).strip().lower().replace("²", "2").replace("³", "3")
    text = text.replace("×", "x")
    return " ".join(text.split())


def default_stats() -> dict:
    return {"questions": {}, "sessions": 0, "total_answered": 0, "total_correct": 0}


def load_json(path: Path, fallback: Any) -> Any:
    try:
        if not path.exists():
            atomic_save_json(path, fallback)
            return fallback
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def atomic_save_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def validate_question_sets(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Question file must contain an object of subject names.")
    cleaned = {}
    for subject, items in data.items():
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("Every subject must have a name.")
        if not isinstance(items, list):
            raise ValueError(f"'{subject}' must contain a question array.")
        cleaned_items = []
        for item in items:
            if not isinstance(item, dict) or not str(item.get("question", "")).strip():
                raise ValueError(f"Invalid question in '{subject}'.")
            answers = item.get("answers")
            if not isinstance(answers, list) or not answers:
                raise ValueError(f"Question '{item.get('question', '')}' needs at least one answer.")
            curriculum = str(item.get("curriculum") or "gcse").strip().lower()
            subject_name = str(item.get("subject") or subject).strip()
            stage = str(item.get("qualification_stage") or "O Level").strip()
            if not get_curriculum(curriculum):
                raise ValueError(f"Unknown curriculum '{curriculum}' in '{item.get('question', '')}'.")
            if subject_name not in subjects_for(curriculum):
                raise ValueError(f"Subject '{subject_name}' is not available for curriculum '{curriculum}'.")
            if stage not in stages_for(curriculum):
                raise ValueError(f"Unknown qualification stage '{stage}' for curriculum '{curriculum}'.")
            tolerance = item.get("numeric_tolerance", 0)
            try:
                tolerance = max(0.0, float(tolerance))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid numeric_tolerance in '{item.get('question', '')}'.")
            choices = item.get("choices", [])
            if not isinstance(choices, list):
                choices = []
            cleaned_items.append({
                "question": str(item["question"]),
                "answers": [str(x) for x in answers],
                "topic": str(item.get("topic") or "General"),
                "choices": [str(x) for x in choices],
                "difficulty": str(item.get("difficulty") or "Normal"),
                "numeric_tolerance": tolerance,
                "curriculum": curriculum,
                "subject": subject_name,
                "qualification_stage": stage,
                "exam_board": str(item.get("exam_board") or ""),
                "paper_reference": str(item.get("paper_reference") or ""),
            })
        cleaned[subject.strip()] = cleaned_items
    return cleaned


def load_questions() -> dict:
    data = load_json(QUESTIONS_FILE, DEFAULT_QUESTIONS)
    try:
        return validate_question_sets(data)
    except ValueError:
        backup = QUESTIONS_FILE.with_name("questions.invalid.json")
        try:
            QUESTIONS_FILE.replace(backup)
        except OSError:
            pass
        save_questions(DEFAULT_QUESTIONS)
        return validate_question_sets(DEFAULT_QUESTIONS)


def save_questions(data: dict) -> None:
    atomic_save_json(QUESTIONS_FILE, validate_question_sets(data))


def load_stats() -> dict:
    value = load_json(STATS_FILE, default_stats())
    if not isinstance(value, dict):
        return default_stats()
    value.setdefault("questions", {})
    value.setdefault("sessions", 0)
    value.setdefault("total_answered", 0)
    value.setdefault("total_correct", 0)
    return value


def save_stats(stats: dict) -> None:
    atomic_save_json(STATS_FILE, stats)


def normalize_process_name(name: str) -> str:
    value = normalize(name)
    return value[:-4] if value.endswith(".exe") else value


def list_windows_processes() -> list[tuple[str, int, str]]:
    result = []
    seen = set()
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            pid = int(proc.info["pid"])
            name = proc.info.get("name") or ""
            exe = Path(proc.info.get("exe") or name).name
            if pid <= 0 or not name:
                continue
            key = (normalize_process_name(exe), normalize(name))
            if key in seen:
                continue
            seen.add(key)
            result.append((name, pid, exe))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
            continue
    return sorted(result, key=lambda x: normalize(x[0]))


def foreground_window() -> tuple[psutil.Process | None, int]:
    if sys.platform != "win32":
        return None, 0
    try:
        import ctypes
        hwnd = int(ctypes.windll.user32.GetForegroundWindow())
        if not hwnd:
            return None, 0
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value), hwnd
    except Exception:
        return None, 0


def is_target_foreground(target_exe: str, target_pid: int | None = None) -> bool:
    proc, _ = foreground_window()
    if not proc:
        return False
    try:
        if target_pid and proc.pid == target_pid:
            return True
        return normalize_process_name(proc.name()) == normalize_process_name(target_exe)
    except psutil.Error:
        return False


def target_window_rect(target_exe: str, target_pid: int | None = None) -> QRect | None:
    proc, hwnd = foreground_window()
    if not proc or not hwnd or not is_target_foreground(target_exe, target_pid):
        return None
    try:
        import ctypes
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rect = RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width <= 0 or height <= 0:
            return None
        return QRect(rect.left, rect.top, width, height)
    except Exception:
        return None


def set_windows_topmost(hwnd: int, topmost: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetWindowPos(hwnd, -1 if topmost else -2, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)
    except Exception:
        pass


class GamePickerDialog(QDialog):
    def __init__(self, parent=None, selected_exe=""):
        super().__init__(parent)
        self.setWindowTitle("Select game")
        self.resize(760, 540)
        self.selected = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the running game. StudyLock monitors only this application's foreground window."))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search processes…")
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Application", "PID", "Executable"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.populate)
        row.addWidget(refresh)
        row.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        row.addWidget(buttons)
        layout.addLayout(row)
        self.search.textChanged.connect(self.populate)
        self.populate()
        self.preselect(selected_exe)

    def populate(self):
        query = normalize(self.search.text())
        self.table.setRowCount(0)
        for name, pid, exe in list_windows_processes():
            if query and query not in normalize(name) and query not in normalize(exe):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(pid)))
            self.table.setItem(row, 2, QTableWidgetItem(exe))

    def preselect(self, selected_exe):
        target = normalize_process_name(selected_exe)
        if not target:
            return
        for row in range(self.table.rowCount()):
            if normalize_process_name(self.table.item(row, 2).text()) == target:
                self.table.selectRow(row)
                break

    def accept_selection(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, APP_NAME, "Select a game first.")
            return
        row = rows[0].row()
        self.selected = {
            "name": self.table.item(row, 0).text(),
            "pid": int(self.table.item(row, 1).text()),
            "exe": self.table.item(row, 2).text(),
        }
        self.accept()


class QuestionOverlay(QWidget):
    """External overlay positioned over the selected game's window only."""
    def __init__(self, question, answer_callback, target_check, rect_callback):
        super().__init__()
        self.question = question
        self.answer_callback = answer_callback
        self.target_check = target_check
        self.rect_callback = rect_callback
        self.allow_close = False
        self.started_at = time.monotonic()
        self.wrong_attempts = 0
        self.setWindowTitle("StudyLock — answer to continue")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#101114; color:white;")

        root = QVBoxLayout(self)
        root.setContentsMargins(70, 50, 70, 50)
        root.setSpacing(18)
        title = QLabel("STUDYLOCK")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        metadata = question.get("topic", "General")
        if question.get("exam_board"):
            metadata += f" • {question['exam_board']}"
        metadata += f" • {question.get('difficulty', 'Normal')}"
        topic = QLabel(metadata)
        topic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        topic.setStyleSheet("color:#9aa0aa;")
        root.addWidget(topic)
        q = QLabel(question["question"])
        q.setWordWrap(True)
        q.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q.setFont(QFont("Segoe UI", 26, QFont.Weight.DemiBold))
        root.addWidget(q, 1)
        choices = question.get("choices", [])
        if choices:
            for choice in choices:
                btn = QPushButton(choice)
                btn.setFont(QFont("Segoe UI", 15))
                btn.clicked.connect(lambda checked=False, c=choice: self.submit(c))
                root.addWidget(btn)
        else:
            self.answer = QLineEdit()
            self.answer.setPlaceholderText("Type your answer…")
            self.answer.setFont(QFont("Segoe UI", 20))
            self.answer.returnPressed.connect(lambda: self.submit(self.answer.text()))
            self.answer.setStyleSheet("padding:14px; border-radius:10px; background:#202329; color:white;")
            root.addWidget(self.answer)
            button = QPushButton("CHECK ANSWER")
            button.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            button.clicked.connect(lambda: self.submit(self.answer.text()))
            root.addWidget(button)
        self.feedback = QLabel("")
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback.setFont(QFont("Segoe UI", 15))
        root.addWidget(self.feedback)
        self.watchdog = QTimer(self)
        self.watchdog.timeout.connect(self.watch_target)
        self.watchdog.start(150)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_to_target()
        self.force_foreground()
        if hasattr(self, "answer"):
            self.answer.setFocus()

    def update_to_target(self):
        rect = self.rect_callback()
        if rect and rect.width() > 0 and rect.height() > 0:
            self.setGeometry(rect)

    def force_foreground(self):
        try:
            hwnd = int(self.winId())
            set_windows_topmost(hwnd, True)
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def watch_target(self):
        try:
            active = bool(self.target_check())
        except Exception:
            active = False
        if not active:
            if self.isVisible():
                self.hide()
            return
        self.update_to_target()
        if not self.isVisible():
            self.show()
        self.force_foreground()

    def submit(self, value: str):
        elapsed = max(0.05, time.monotonic() - self.started_at)
        correct = self.answer_callback(value, elapsed, self.wrong_attempts)
        if correct:
            self.allow_close = True
            self.close()
        else:
            self.wrong_attempts += 1
            self.feedback.setText("❌ Not quite — try again.")
            if hasattr(self, "answer"):
                self.answer.selectAll()
                self.answer.setFocus()
            self.force_foreground()

    def closeEvent(self, event: QCloseEvent):
        if not self.allow_close:
            event.ignore()
            self.force_foreground()
            return
        super().closeEvent(event)


class AnalyticsDialog(QDialog):
    def __init__(self, stats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("StudyLock — Topic Performance")
        self.resize(1050, 620)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Accuracy is the main signal. Speed and wrong attempts help identify weak points; being fast but inaccurate is still weak."))
        table = QTableWidget(0, 9)
        table.setHorizontalHeaderLabels(["Curriculum", "Subject", "Stage", "Topic", "Answered", "Accuracy", "Avg speed", "Mastery", "Recommendation"])
        table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(table)
        rows = []
        for key, s in stats.get("questions", {}).items():
            answered = int(s.get("answered", 0))
            correct = int(s.get("correct", 0))
            wrong = int(s.get("wrong", 0))
            avg = float(s.get("answer_time_total", 0)) / answered if answered else 0
            accuracy = correct / answered * 100 if answered else 0
            speed_score = 100 if avg <= 8 else max(0, 100 - (avg - 8) * 3)
            wrong_rate = wrong / max(1, answered)
            mastery = max(0, min(100, accuracy * 0.75 + speed_score * 0.25 - min(25, wrong_rate * 25)))
            if mastery >= 85 and accuracy >= 85:
                rec = "Strong — maintain it"
            elif mastery >= 70 and accuracy >= 70:
                rec = "Good — practice occasionally"
            elif accuracy >= 55:
                rec = "Needs practice"
            else:
                rec = "Weak point — prioritize practice"
            rows.append((mastery, s, answered, accuracy, avg, rec))
        rows.sort(key=lambda x: x[0])
        for mastery, s, answered, accuracy, avg, rec in rows:
            row = table.rowCount()
            table.insertRow(row)
            values = [str(s.get("curriculum", "")), str(s.get("subject", "")), str(s.get("qualification_stage", "")), str(s.get("topic", key)), str(answered), f"{accuracy:.0f}%", f"{avg:.1f}s", f"{mastery:.0f}/100", rec]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))
        if not rows:
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem("No data yet — complete some questions first."))
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        root.addWidget(close)


class StudyLock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.questions = load_questions()
        self.stats = load_stats()
        self.settings = load_json(SETTINGS_FILE, {})
        self.locked = False
        self.remaining = 0.0
        self.last_tick = time.monotonic()
        self.current_question = None
        self.target_exe = str(self.settings.get("target_exe", ""))
        self.target_pid = self.settings.get("target_pid")
        self.target_display = str(self.settings.get("target_display", ""))
        self.overlay = None
        self.recent_question_ids = []
        self.build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(250)

    def build_ui(self):
        self.setWindowTitle(APP_NAME)
        self.resize(980, 720)
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        home = QWidget()
        root = QVBoxLayout(home)
        root.setContentsMargins(35, 30, 35, 30)
        root.setSpacing(15)
        title = QLabel("StudyLock")
        title.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        root.addWidget(title)
        root.addWidget(QLabel("StudyLock asks questions from the exact curriculum / subject / qualification you select."))

        form = QFormLayout()
        self.curriculum = QComboBox()
        for item in available_curricula():
            self.curriculum.addItem(item.name, item.id)
        self.subject = QComboBox()
        self.stage = QComboBox()
        self.curriculum.currentIndexChanged.connect(self.curriculum_changed)
        self.subject.currentIndexChanged.connect(self.selection_changed)
        self.stage.currentIndexChanged.connect(self.selection_changed)
        form.addRow("Curriculum", self.curriculum)
        form.addRow("Subject", self.subject)
        form.addRow("Qualification", self.stage)
        self.interval = QSpinBox()
        self.interval.setRange(1, 180)
        self.interval.setValue(int(self.settings.get("interval_minutes", 20)))
        self.interval.setSuffix(" min")
        form.addRow("Question every", self.interval)
        root.addLayout(form)

        self.course_status = QLabel()
        self.course_status.setWordWrap(True)
        root.addWidget(self.course_status)
        self.curriculum_changed()

        game_row = QHBoxLayout()
        self.game_label = QLabel(self.target_display or "No game selected")
        self.game_label.setWordWrap(True)
        select_game = QPushButton("Select game…")
        select_game.clicked.connect(self.select_game)
        clear_game = QPushButton("Clear")
        clear_game.clicked.connect(self.clear_game)
        game_row.addWidget(self.game_label, 1)
        game_row.addWidget(select_game)
        game_row.addWidget(clear_game)
        root.addLayout(game_row)
        note = QLabel("🔒 Only the selected game is subject to StudyLock. Alt+Tab to Chrome, Google, Discord or another app whenever needed. The pending question returns when you return to the game.")
        note.setWordWrap(True)
        root.addWidget(note)

        buttons = QHBoxLayout()
        start = QPushButton("▶ Start StudyLock")
        start.clicked.connect(self.start_lock)
        stop = QPushButton("■ Stop")
        stop.clicked.connect(self.stop_lock)
        analytics = QPushButton("📊 Topic Performance")
        analytics.clicked.connect(self.show_analytics)
        import_btn = QPushButton("Import questions")
        import_btn.clicked.connect(self.import_json)
        export_btn = QPushButton("Export questions")
        export_btn.clicked.connect(self.export_json)
        buttons.addWidget(start)
        buttons.addWidget(stop)
        buttons.addWidget(analytics)
        buttons.addWidget(import_btn)
        buttons.addWidget(export_btn)
        root.addLayout(buttons)

        self.status = QLabel("Ready")
        self.status.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        root.addWidget(self.status)
        self.details = QLabel("Choose a curriculum, subject and qualification, select a game, then start.")
        self.details.setWordWrap(True)
        root.addWidget(self.details)
        root.addStretch()

        sets = QWidget()
        sets_root = QVBoxLayout(sets)
        sets_root.addWidget(QLabel("Loaded question bank"))
        self.list_widget = QListWidget()
        sets_root.addWidget(self.list_widget)
        self.refresh_subjects()
        tabs.addTab(home, "Session")
        tabs.addTab(sets, "Question Bank")

    def current_selection(self):
        return (
            str(self.curriculum.currentData() or "").strip().lower(),
            self.subject.currentText().strip(),
            self.stage.currentText().strip(),
        )

    def curriculum_changed(self):
        curriculum_id = str(self.curriculum.currentData() or "")
        self.subject.blockSignals(True)
        self.stage.blockSignals(True)
        self.subject.clear()
        self.subject.addItems(subjects_for(curriculum_id))
        self.stage.clear()
        self.stage.addItems(stages_for(curriculum_id))
        saved = self.settings.get("subject")
        if saved in subjects_for(curriculum_id):
            self.subject.setCurrentText(saved)
        saved_stage = self.settings.get("qualification_stage")
        if saved_stage in stages_for(curriculum_id):
            self.stage.setCurrentText(saved_stage)
        self.subject.blockSignals(False)
        self.stage.blockSignals(False)
        self.selection_changed()

    def selection_changed(self):
        curriculum_id, subject, stage = self.current_selection()
        count = len(self.filtered_questions()) if hasattr(self, "questions") else 0
        curriculum = get_curriculum(curriculum_id)
        name = curriculum.name if curriculum else curriculum_id
        self.course_status.setText(f"Course: {name} → {subject} → {stage} | {count} matching questions loaded")
        if hasattr(self, "settings"):
            self.settings.update({"curriculum": curriculum_id, "subject": subject, "qualification_stage": stage})
            atomic_save_json(SETTINGS_FILE, self.settings)

    def filtered_questions(self):
        curriculum_id, subject, stage = self.current_selection()
        pool = self.questions.get(subject, [])
        return [q for q in pool if q.get("curriculum") == curriculum_id and q.get("subject") == subject and q.get("qualification_stage") == stage]

    def refresh_subjects(self):
        self.list_widget.clear()
        for curriculum in available_curricula():
            for subject in curriculum.subjects:
                for stage in curriculum.qualification_stages:
                    count = sum(1 for q in self.questions.get(subject, []) if q.get("curriculum") == curriculum.id and q.get("qualification_stage") == stage)
                    self.list_widget.addItem(f"{curriculum.name} → {subject} → {stage}: {count} questions")

    def select_game(self):
        dialog = GamePickerDialog(self, self.target_exe)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected:
            self.target_exe = dialog.selected["exe"]
            self.target_pid = dialog.selected["pid"]
            self.target_display = f"{dialog.selected['name']} ({dialog.selected['exe']})"
            self.game_label.setText("Selected: " + self.target_display)
            self.settings.update({"target_exe": self.target_exe, "target_pid": self.target_pid, "target_display": self.target_display})
            atomic_save_json(SETTINGS_FILE, self.settings)

    def clear_game(self):
        self.target_exe = ""
        self.target_pid = None
        self.target_display = ""
        self.game_label.setText("No game selected — select one before starting")
        for key in ("target_exe", "target_pid", "target_display"):
            self.settings.pop(key, None)
        atomic_save_json(SETTINGS_FILE, self.settings)

    def target_is_foreground(self):
        return bool(self.target_exe) and is_target_foreground(self.target_exe, self.target_pid)

    def target_rect(self):
        return target_window_rect(self.target_exe, self.target_pid)

    def start_lock(self):
        pool = self.filtered_questions()
        if not pool:
            QMessageBox.warning(self, APP_NAME, "No questions are loaded for this exact curriculum, subject and qualification. Import the appropriate question bank first.")
            return
        if not self.target_exe:
            QMessageBox.warning(self, APP_NAME, "Select a game first. StudyLock locks the selected game only.")
            return
        self.locked = True
        self.remaining = self.interval.value() * 60.0
        self.last_tick = time.monotonic()
        self.current_question = None
        self.recent_question_ids.clear()
        self.stats["sessions"] = int(self.stats.get("sessions", 0)) + 1
        save_stats(self.stats)
        self.settings["interval_minutes"] = self.interval.value()
        atomic_save_json(SETTINGS_FILE, self.settings)
        self.status.setText("RUNNING — game time earned")
        self.details.setText(f"Watching only: {self.target_display}. The timer advances only while that selected game is the foreground app.")

    def stop_lock(self):
        self.locked = False
        self.current_question = None
        if self.overlay:
            self.overlay.allow_close = True
            self.overlay.close()
            self.overlay = None
        self.status.setText("Stopped")
        self.details.setText("Ready")

    def choose_question(self):
        pool = self.filtered_questions()
        if not pool:
            return None
        candidates = [i for i in range(len(pool)) if i not in self.recent_question_ids]
        if not candidates:
            candidates = list(range(len(pool)))
            self.recent_question_ids.clear()
        idx = random.choice(candidates)
        self.recent_question_ids.append(idx)
        self.recent_question_ids = self.recent_question_ids[-min(10, len(pool)):]
        return pool[idx]

    def tick(self):
        now = time.monotonic()
        elapsed = max(0.0, min(2.0, now - self.last_tick))
        self.last_tick = now
        if not self.locked:
            return
        if self.current_question:
            if self.target_is_foreground():
                if self.overlay is None:
                    self.show_question_overlay()
                elif not self.overlay.isVisible():
                    self.overlay.show()
                self.status.setText("LOCKED — answer the question to continue")
            else:
                self.status.setText("QUESTION WAITING — other apps are available")
            return
        if not self.target_is_foreground():
            self.status.setText("PAUSED — selected game is not active")
            return
        self.remaining -= elapsed
        if self.remaining <= 0:
            self.show_question()
        else:
            mins = int(self.remaining // 60)
            secs = int(self.remaining % 60)
            self.status.setText(f"RUNNING — next question in {mins:02d}:{secs:02d}")

    def show_question(self):
        self.current_question = self.choose_question()
        if not self.current_question:
            self.stop_lock()
            return
        self.show_question_overlay()

    def show_question_overlay(self):
        if not self.current_question or not self.target_is_foreground():
            return
        rect = self.target_rect()
        if not rect:
            self.status.setText("LOCKED — selected game window cannot be positioned for the external overlay")
            self.details.setText("If this game uses exclusive fullscreen, switch it to borderless/windowed mode. StudyLock does not inject into or modify the game.")
            return
        if self.overlay is not None:
            self.overlay.update_to_target()
            if not self.overlay.isVisible():
                self.overlay.show()
            self.overlay.force_foreground()
            return
        self.overlay = QuestionOverlay(self.current_question, self.question_finished, self.target_is_foreground, self.target_rect)
        self.overlay.setGeometry(rect)
        self.overlay.show()
        self.status.setText("LOCKED — answer the question to continue")

    def stats_key(self, question):
        curriculum_id, subject, stage = self.current_selection()
        topic = str(question.get("topic") or "General")
        return f"{curriculum_id}::{subject}::{stage}::{topic}"

    def make_stat_item(self, question):
        curriculum_id, subject, stage = self.current_selection()
        return {
            "curriculum": curriculum_id,
            "subject": subject,
            "qualification_stage": stage,
            "topic": str(question.get("topic") or "General"),
            "answered": 0,
            "correct": 0,
            "wrong": 0,
            "answer_time_total": 0.0,
            "best_time": None,
            "recent": [],
        }

    def record_wrong_attempt(self, question):
        key = self.stats_key(question)
        item = self.stats["questions"].setdefault(key, self.make_stat_item(question))
        item["wrong"] = int(item.get("wrong", 0)) + 1
        save_stats(self.stats)

    def record_correct(self, question, answer_time, wrong_attempts):
        key = self.stats_key(question)
        item = self.stats["questions"].setdefault(key, self.make_stat_item(question))
        item["answered"] = int(item.get("answered", 0)) + 1
        item["correct"] = int(item.get("correct", 0)) + 1
        item["answer_time_total"] = float(item.get("answer_time_total", 0)) + float(answer_time)
        if item.get("best_time") is None or answer_time < float(item["best_time"]):
            item["best_time"] = float(answer_time)
        item["recent"] = (item.get("recent", []) + [{"correct": True, "time": answer_time, "wrong_attempts": wrong_attempts}])[-20:]
        self.stats["total_answered"] = int(self.stats.get("total_answered", 0)) + 1
        self.stats["total_correct"] = int(self.stats.get("total_correct", 0)) + 1
        save_stats(self.stats)

    def question_finished(self, value, elapsed, wrong_attempts):
        question = self.current_question
        if not question:
            return False
        normalized = normalize(value)
        accepted = {normalize(x) for x in question.get("answers", [])}
        correct = normalized in accepted
        tolerance = float(question.get("numeric_tolerance", 0) or 0)
        if not correct and tolerance:
            try:
                user_num = float(normalized.replace(",", "."))
                for answer in accepted:
                    cleaned = answer.replace(",", ".")
                    numeric_chars = "0123456789.-+eE"
                    numeric = "".join(ch for ch in cleaned if ch in numeric_chars)
                    if numeric and math.isclose(user_num, float(numeric), abs_tol=tolerance):
                        correct = True
                        break
            except (ValueError, TypeError):
                pass
        if not correct:
            self.record_wrong_attempt(question)
            return False
        self.record_correct(question, elapsed, wrong_attempts)
        self.current_question = None
        self.remaining = self.interval.value() * 60.0
        if self.overlay:
            self.overlay.allow_close = True
            self.overlay.close()
            self.overlay = None
        self.status.setText("✅ Correct — game unlocked")
        return True

    def show_analytics(self):
        AnalyticsDialog(self.stats, self).exec()

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import curriculum question bank", "", "JSON files (*.json)")
        if not path:
            return
        try:
            data = validate_question_sets(json.loads(Path(path).read_text(encoding="utf-8")))
            self.questions = data
            save_questions(data)
            self.refresh_subjects()
            self.selection_changed()
            QMessageBox.information(self, APP_NAME, "Question bank imported successfully. Questions are filtered by curriculum, subject and qualification.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not import questions:\n{exc}")

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export curriculum question bank", "StudyLock-questions.json", "JSON files (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.questions, indent=2, ensure_ascii=False), encoding="utf-8")
            QMessageBox.information(self, APP_NAME, "Question bank exported successfully.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not export questions:\n{exc}")

    def closeEvent(self, event):
        if self.locked:
            answer = QMessageBox.question(self, APP_NAME, "A StudyLock session is active. Stop the session and exit?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.stop_lock()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    if sys.platform != "win32":
        QMessageBox.warning(None, APP_NAME, "StudyLock's game detection and external lock are designed for Windows.")
    window = StudyLock()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
