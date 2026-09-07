import json
import math
import os
import random
import re
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
    QTableWidgetItem, QTabWidget, QCheckBox
)

APP_NAME = "StudyLock"
DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "StudyLock"
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUESTIONS_FILE = DATA_DIR / "questions.json"
STATS_FILE = DATA_DIR / "stats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_QUESTIONS = {
    "Chemistry": [
        {"question": "What is the charge of a proton?", "answers": ["+1", "positive one", "1"], "topic": "Atomic structure"},
        {"question": "What is the chemical symbol for sodium?", "answers": ["Na"], "topic": "Atomic structure"},
    ],
    "Physics": [
        {"question": "What is the SI unit of force?", "answers": ["N", "newton", "newtons"], "topic": "Forces"},
        {"question": "What is the approximate acceleration due to gravity on Earth?", "answers": ["9.8", "9.81", "9.8 m/s2", "9.81 m/s2"], "topic": "Forces"},
    ],
    "Math": [
        {"question": "What is 12 × 8?", "answers": ["96"], "topic": "Arithmetic"},
        {"question": "What is the square root of 81?", "answers": ["9"], "topic": "Arithmetic"},
    ],
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
            path.write_text(json.dumps(fallback, indent=2, ensure_ascii=False), encoding="utf-8")
            return fallback
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return fallback


def atomic_save_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_questions() -> dict:
    data = load_json(QUESTIONS_FILE, DEFAULT_QUESTIONS)
    return validate_question_sets(data)


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
            cleaned_items.append({
                "question": str(item["question"]),
                "answers": [str(x) for x in answers],
                "topic": str(item.get("topic") or "General"),
                "choices": [str(x) for x in item.get("choices", [])] if isinstance(item.get("choices", []), list) else [],
                "difficulty": str(item.get("difficulty") or "Normal"),
                "numeric_tolerance": float(item.get("numeric_tolerance", 0)) if item.get("numeric_tolerance") not in (None, "") else 0.0,
            })
        cleaned[subject.strip()] = cleaned_items
    return cleaned


def save_questions(data: dict) -> None:
    atomic_save_json(QUESTIONS_FILE, data)


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
    """Return (display name, pid, executable name) for visible-ish user processes."""
    result = []
    seen = set()
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            pid = int(proc.info["pid"])
            name = proc.info.get("name") or ""
            exe = Path(proc.info.get("exe") or name).name
            if pid <= 0 or not name or pid in seen:
                continue
            key = (normalize_process_name(exe), normalize(name))
            if key in seen:
                continue
            seen.add(key)
            result.append((name, pid, exe))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
            continue
    return sorted(result, key=lambda x: normalize(x[0]))


def foreground_process() -> psutil.Process | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value)
    except Exception:
        return None


def foreground_pid() -> int | None:
    proc = foreground_process()
    try:
        return proc.pid if proc else None
    except psutil.Error:
        return None


def is_target_foreground(target_exe: str, target_pid: int | None = None) -> bool:
    proc = foreground_process()
    if not proc:
        return False
    try:
        if target_pid and proc.pid == target_pid:
            return True
        return normalize_process_name(proc.name()) == normalize_process_name(target_exe)
    except psutil.Error:
        return False


def set_windows_topmost(hwnd: int, topmost: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(hwnd, HWND_TOPMOST if topmost else HWND_NOTOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    except Exception:
        pass


class GamePickerDialog(QDialog):
    def __init__(self, parent=None, selected_exe=""):
        super().__init__(parent)
        self.setWindowTitle("Select game")
        self.resize(720, 520)
        self.selected = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose the Windows game/application that StudyLock should lock."))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search processes…")
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Application", "PID", "Executable"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.populate)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_selection)
        buttons.rejected.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(self.refresh_button)
        row.addStretch()
        row.addWidget(buttons)
        layout.addLayout(row)
        self.search.textChanged.connect(self.populate)
        self.populate()
        self.preselect(selected_exe)

    def populate(self):
        query = normalize(self.search.text())
        processes = list_windows_processes()
        self.table.setRowCount(0)
        for name, pid, exe in processes:
            if query and query not in normalize(name) and query not in normalize(exe):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(pid)))
            self.table.setItem(row, 2, QTableWidgetItem(exe))

    def preselect(self, selected_exe):
        if not selected_exe:
            return
        target = normalize_process_name(selected_exe)
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
    """External overlay. It never injects into, modifies, or sends input to the game."""
    def __init__(self, question, answer_callback, leave_callback):
        super().__init__()
        self.question = question
        self.answer_callback = answer_callback
        self.leave_callback = leave_callback
        self.allow_close = False
        self.started_at = time.monotonic()
        self.wrong_attempts = 0
        self.setWindowTitle("StudyLock — answer to continue")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#101114; color:white;")

        root = QVBoxLayout(self)
        root.setContentsMargins(90, 70, 90, 70)
        root.setSpacing(22)
        title = QLabel("STUDYLOCK")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        topic = QLabel(f"{question.get('topic', 'General')} • {question.get('difficulty', 'Normal')}")
        topic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        topic.setStyleSheet("color:#9aa0aa;")
        root.addWidget(topic)
        q = QLabel(question["question"])
        q.setWordWrap(True)
        q.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q.setFont(QFont("Segoe UI", 30, QFont.Weight.DemiBold))
        root.addWidget(q, 1)

        choices = question.get("choices", [])
        if choices:
            for choice in choices:
                btn = QPushButton(choice)
                btn.setFont(QFont("Segoe UI", 16))
                btn.clicked.connect(lambda checked=False, c=choice: self.submit(c))
                root.addWidget(btn)
        else:
            self.answer = QLineEdit()
            self.answer.setPlaceholderText("Type your answer…")
            self.answer.setFont(QFont("Segoe UI", 22))
            self.answer.returnPressed.connect(lambda: self.submit(self.answer.text()))
            self.answer.setStyleSheet("padding:16px; border-radius:10px; background:#202329; color:white;")
            root.addWidget(self.answer)
            self.answer.setFocus()
            button = QPushButton("CHECK ANSWER")
            button.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            button.clicked.connect(lambda: self.submit(self.answer.text()))
            root.addWidget(button)

        self.feedback = QLabel("")
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback.setFont(QFont("Segoe UI", 16))
        root.addWidget(self.feedback)

        self.watchdog = QTimer(self)
        self.watchdog.timeout.connect(self.watch_target)
        self.watchdog.start(150)

    def showEvent(self, event):
        super().showEvent(event)
        self.cover_virtual_desktop()
        self.force_foreground()

    def cover_virtual_desktop(self):
        screens = QApplication.screens()
        if not screens:
            return
        rect = QRect()
        for screen in screens:
            rect = screen.geometry() if rect.isNull() else rect.united(screen.geometry())
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
        # Emergency behavior: leaving the selected game is allowed. The overlay hides,
        # but the game remains locked because the question is still pending. Returning
        # to the selected game immediately restores the question.
        proc = foreground_process()
        if proc is None:
            return
        try:
            # The target is supplied by the controller; callback decides whether the
            # current foreground app is still the selected game.
            if not self.is_target_foreground():
                self.hide()
                self.leave_callback()
            elif not self.isVisible():
                self.show()
                self.cover_virtual_desktop()
                self.force_foreground()
        except Exception:
            pass

    def is_target_foreground(self):
        return self.leave_callback.__self__.target_is_foreground() if hasattr(self.leave_callback, "__self__") else True

    def submit(self, value: str):
        elapsed = max(0.05, time.monotonic() - self.started_at)
        if self.answer_callback(value, elapsed, self.wrong_attempts):
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
        self.resize(900, 560)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Your weak points are based on accuracy, answer speed, wrong attempts, and recent performance. Speed is never used to excuse incorrect answers."))
        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(["Topic", "Questions", "Accuracy", "Avg speed", "Wrong attempts", "Mastery", "Recommendation"])
        table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(table)
        rows = []
        for topic, s in stats.get("questions", {}).items():
            answered = int(s.get("answered", 0))
            correct = int(s.get("correct", 0))
            wrong = int(s.get("wrong", 0))
            avg = float(s.get("answer_time_total", 0)) / answered if answered else 0
            accuracy = correct / answered * 100 if answered else 0
            # Accuracy is dominant; speed and recent wrong attempts refine the score.
            speed_score = 100 if avg <= 8 else max(0, 100 - (avg - 8) * 3)
            wrong_penalty = min(25, wrong / max(1, answered) * 100 * 0.25)
            mastery = max(0, min(100, accuracy * 0.75 + speed_score * 0.25 - wrong_penalty))
            if mastery >= 85 and accuracy >= 85:
                rec = "Strong — maintain it"
            elif mastery >= 70 and accuracy >= 70:
                rec = "Good — practice occasionally"
            elif accuracy >= 55:
                rec = "Needs practice"
            else:
                rec = "Weak point — prioritize practice"
            rows.append((mastery, topic, answered, accuracy, avg, wrong, rec))
        rows.sort(key=lambda x: x[0])
        for mastery, topic, answered, accuracy, avg, wrong, rec in rows:
            row = table.rowCount()
            table.insertRow(row)
            values = [topic, str(answered), f"{accuracy:.0f}%", f"{avg:.1f}s", str(wrong), f"{mastery:.0f}/100", rec]
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
        self.current_question_index = -1
        self.question_pool_key = ""
        self.target_exe = str(self.settings.get("target_exe", ""))
        self.target_pid = self.settings.get("target_pid")
        self.target_display = str(self.settings.get("target_display", ""))
        self.overlay = None
        self.session_wrong = 0
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
        root.setSpacing(16)
        title = QLabel("StudyLock")
        title.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        root.addWidget(title)
        root.addWidget(QLabel("Study first. Earn your game time — without modifying the game."))

        form = QFormLayout()
        self.subject = QComboBox()
        self.subject.addItems(sorted(self.questions.keys()))
        self.interval = QSpinBox()
        self.interval.setRange(1, 180)
        self.interval.setValue(int(self.settings.get("interval_minutes", 20)))
        self.interval.setSuffix(" min")
        form.addRow("Question set", self.subject)
        form.addRow("Question every", self.interval)
        root.addLayout(form)

        game_row = QHBoxLayout()
        self.game_label = QLabel()
        self.game_label.setText(self.target_display or "No game selected")
        self.game_label.setWordWrap(True)
        select_game = QPushButton("Select game…")
        select_game.clicked.connect(self.select_game)
        clear_game = QPushButton("Clear")
        clear_game.clicked.connect(self.clear_game)
        game_row.addWidget(self.game_label, 1)
        game_row.addWidget(select_game)
        game_row.addWidget(clear_game)
        root.addLayout(game_row)

        self.any_app = QCheckBox("Lock the selected game only (recommended)")
        self.any_app.setChecked(True)
        self.any_app.setEnabled(False)
        root.addWidget(self.any_app)

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
        self.details = QLabel("Select a game, choose a question set, and start. Leaving the selected game for an emergency is allowed; the pending question returns when you return to the game."))
        self.details.setWordWrap(True)
        root.addWidget(self.details)
        root.addStretch()

        sets = QWidget()
        sets_root = QVBoxLayout(sets)
        sets_root.addWidget(QLabel("Question sets"))
        self.list_widget = QListWidget()
        sets_root.addWidget(self.list_widget)
        self.refresh_subjects()
        tabs.addTab(home, "Session")
        tabs.addTab(sets, "Question Sets")

    def refresh_subjects(self):
        self.list_widget.clear()
        for name, items in self.questions.items():
            self.list_widget.addItem(f"{name} — {len(items)} questions")

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
        self.settings.pop("target_exe", None)
        self.settings.pop("target_pid", None)
        self.settings.pop("target_display", None)
        atomic_save_json(SETTINGS_FILE, self.settings)

    def target_is_foreground(self):
        return bool(self.target_exe) and is_target_foreground(self.target_exe, self.target_pid)

    def start_lock(self):
        pool = self.questions.get(self.subject.currentText(), [])
        if not pool:
            QMessageBox.warning(self, APP_NAME, "This question set has no questions.")
            return
        if not self.target_exe:
            QMessageBox.warning(self, APP_NAME, "Select a game first. StudyLock locks the selected game only.")
            return
        self.locked = True
        self.remaining = self.interval.value() * 60.0
        self.last_tick = time.monotonic()
        self.current_question = None
        self.session_wrong = 0
        self.recent_question_ids.clear()
        self.stats["sessions"] = int(self.stats.get("sessions", 0)) + 1
        save_stats(self.stats)
        self.settings["interval_minutes"] = self.interval.value()
        atomic_save_json(SETTINGS_FILE, self.settings)
        self.status.setText("RUNNING — game time earned")
        self.details.setText(f"Watching only: {self.target_display}. Other apps remain available.")

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
        pool = self.questions.get(self.subject.currentText(), [])
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

        # If a question is pending, only show it when the selected game has focus.
        if self.current_question:
            if self.target_is_foreground():
                if self.overlay is None or not self.overlay.isVisible():
                    self.show_question_overlay()
                self.status.setText("LOCKED — answer the question to continue")
            else:
                self.status.setText("QUESTION WAITING — other apps are available")
            return

        # The timer represents time spent in the selected game, not time spent in Chrome.
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
        if not self.current_question or self.overlay is not None:
            return
        self.overlay = QuestionOverlay(self.current_question, self.question_finished, self.on_overlay_left_game)
        self.overlay.show()
        self.status.setText("LOCKED — answer the question to continue")

    def on_overlay_left_game(self):
        # Do not destroy the pending question. It is the lock attached to this game.
        if self.current_question:
            self.status.setText("QUESTION WAITING — other apps are available")

    def record_result(self, question, correct, answer_time, wrong_attempts):
        topic = str(question.get("topic") or "General")
        key = f"{self.subject.currentText()}::{topic}"
        item = self.stats["questions"].setdefault(key, {
            "subject": self.subject.currentText(), "topic": topic, "answered": 0,
            "correct": 0, "wrong": 0, "answer_time_total": 0.0,
            "best_time": None, "recent": []
        })
        item["answered"] += 1
        item["wrong"] += int(wrong_attempts)
        item["answer_time_total"] += float(answer_time)
        if correct:
            item["correct"] += 1
        if item["best_time"] is None or answer_time < float(item["best_time"]):
            item["best_time"] = float(answer_time)
        item["recent"] = (item.get("recent", []) + [{"correct": correct, "time": answer_time}])[-20:]
        self.stats["total_answered"] = int(self.stats.get("total_answered", 0)) + 1
        if correct:
            self.stats["total_correct"] = int(self.stats.get("total_correct", 0)) + 1
        save_stats(self.stats)

    def question_finished(self, value, elapsed, wrong_attempts):
        question = self.current_question
        if not question:
            return False
        normalized = normalize(value)
        accepted = {normalize(x) for x in question.get("answers", [])}
        correct = normalized in accepted
        if not correct and question.get("numeric_tolerance", 0):
            try:
                user_num = float(normalized.replace(",", "."))
                for answer in accepted:
                    expected = float(answer.replace(",", ".").replace("m/s2", "").strip())
                    if math.isclose(user_num, expected, abs_tol=float(question["numeric_tolerance"])):
                        correct = True
                        break
            except (ValueError, TypeError):
                pass
        if not correct:
            # Wrong attempts are recorded only when the question is eventually solved,
            # so the topic gets a complete picture without creating duplicate questions.
            return False

        self.record_result(question, True, elapsed, wrong_attempts)
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
        path, _ = QFileDialog.getOpenFileName(self, "Import question sets", "", "JSON files (*.json)")
        if not path:
            return
        try:
            data = validate_question_sets(json.loads(Path(path).read_text(encoding="utf-8")))
            self.questions = data
            save_questions(data)
            self.subject.clear()
            self.subject.addItems(sorted(self.questions.keys()))
            self.refresh_subjects()
            QMessageBox.information(self, APP_NAME, "Question sets imported successfully.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not import questions:\n{exc}")

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export question sets", "StudyLock-questions.json", "JSON files (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.questions, indent=2, ensure_ascii=False), encoding="utf-8")
            QMessageBox.information(self, APP_NAME, "Question sets exported successfully.")
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
    app.setQuitOnLastWindowClosed(True)
    if sys.platform != "win32":
        QMessageBox.warning(None, APP_NAME, "StudyLock's game detection and external lock are currently designed for Windows.")
    window = StudyLock()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
