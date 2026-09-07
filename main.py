import json
import os
import sys
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QVBoxLayout, QWidget
)

APP_NAME = "StudyLock"
DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "StudyLock"
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUESTIONS_FILE = DATA_DIR / "questions.json"

DEFAULT_QUESTIONS = {
    "Chemistry": [
        {"question": "What is the charge of a proton?", "answers": ["+1", "positive one", "1"]},
        {"question": "What is the chemical symbol for sodium?", "answers": ["Na"]},
    ],
    "Physics": [
        {"question": "What is the SI unit of force?", "answers": ["N", "newton", "newtons"]},
        {"question": "What is the approximate acceleration due to gravity on Earth?", "answers": ["9.8", "9.81", "9.8 m/s2", "9.81 m/s2"]},
    ],
    "Math": [
        {"question": "What is 12 × 8?", "answers": ["96"]},
        {"question": "What is the square root of 81?", "answers": ["9"]},
    ],
}


def normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("²", "2").split())


def load_questions():
    if not QUESTIONS_FILE.exists():
        QUESTIONS_FILE.write_text(json.dumps(DEFAULT_QUESTIONS, indent=2), encoding="utf-8")
    try:
        data = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else DEFAULT_QUESTIONS.copy()
    except Exception:
        return DEFAULT_QUESTIONS.copy()


def save_questions(data):
    QUESTIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def foreground_process():
    if sys.platform != "win32":
        return None
    import ctypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        return psutil.Process(pid.value)
    except Exception:
        return None


class QuestionOverlay(QWidget):
    """External Windows lock overlay; never injects into or modifies a game."""

    def __init__(self, question, answer_callback):
        super().__init__()
        self.answer_callback = answer_callback
        self.question = question
        self.setWindowTitle("StudyLock — Answer to continue")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#101114; color:white;")

        root = QVBoxLayout(self)
        root.setContentsMargins(80, 70, 80, 70)
        root.setSpacing(24)

        title = QLabel("STUDYLOCK")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        self.question_label = QLabel(question["question"])
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question_label.setFont(QFont("Segoe UI", 30, QFont.Weight.DemiBold))
        root.addWidget(self.question_label, 1)

        self.answer = QLineEdit()
        self.answer.setPlaceholderText("Type your answer…")
        self.answer.setFont(QFont("Segoe UI", 22))
        self.answer.returnPressed.connect(self.check)
        self.answer.setStyleSheet("padding:16px; border-radius:10px; background:#202329; color:white;")
        root.addWidget(self.answer)

        self.feedback = QLabel("")
        self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback.setFont(QFont("Segoe UI", 16))
        root.addWidget(self.feedback)

        button = QPushButton("UNLOCK GAME")
        button.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        button.clicked.connect(self.check)
        root.addWidget(button)

    def showEvent(self, event):
        super().showEvent(event)
        self.cover_all_screens()
        self.answer.setFocus()
        self.force_foreground()

    def cover_all_screens(self):
        screens = QApplication.screens()
        if not screens:
            return
        # A single window cannot span disjoint monitors perfectly, so use the
        # virtual desktop geometry. This covers normal multi-monitor layouts.
        rect = screens[0].geometry()
        for screen in screens[1:]:
            rect = rect.united(screen.geometry())
        self.setGeometry(rect)

    def force_foreground(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            HWND_TOPMOST = -1
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def check(self):
        value = normalize(self.answer.text())
        accepted = {normalize(str(x)) for x in self.question.get("answers", [])}
        if value in accepted:
            self.answer_callback(True)
            self.close()
        else:
            self.feedback.setText("Not quite — try again.")
            self.answer.selectAll()
            self.answer.setFocus()
            self.force_foreground()

    def keyPressEvent(self, event):
        # Escape cannot dismiss the lock screen.
        if event.key() == Qt.Key.Key_Escape:
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Only the app's own correct-answer path should dismiss the overlay.
        if not getattr(self, "_unlocking", False):
            event.ignore()
            return
        super().closeEvent(event)

    def unlock_and_close(self):
        self._unlocking = True
        self.close()


class StudyLock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.questions = load_questions()
        self.locked = False
        self.remaining = 0
        self.current_question = None
        self.target_process_name = ""
        self.overlay = None

        self.setWindowTitle(APP_NAME)
        self.resize(900, 650)
        self.build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

        # Lightweight focus watchdog. It only runs while a question is active.
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.keep_overlay_foreground)
        self.focus_timer.start(250)

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(35, 30, 35, 30)
        root.setSpacing(18)

        title = QLabel("StudyLock")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        subtitle = QLabel("Study first. Earn your game time.")
        subtitle.setStyleSheet("color:#777;")
        root.addWidget(title)
        root.addWidget(subtitle)

        form = QFormLayout()
        self.subject = QComboBox()
        self.subject.addItems(sorted(self.questions.keys()))
        self.interval = QSpinBox()
        self.interval.setRange(1, 180)
        self.interval.setValue(20)
        self.interval.setSuffix(" min")
        self.game = QLineEdit()
        self.game.setPlaceholderText("Optional: Fortnite, Siege, Roblox… (blank = any app)")
        form.addRow("Question set", self.subject)
        form.addRow("Question every", self.interval)
        form.addRow("Target app", self.game)
        root.addLayout(form)

        buttons = QHBoxLayout()
        start = QPushButton("Start StudyLock")
        start.clicked.connect(self.start_lock)
        stop = QPushButton("Stop")
        stop.clicked.connect(self.stop_lock)
        import_btn = QPushButton("Import JSON")
        import_btn.clicked.connect(self.import_json)
        buttons.addWidget(start)
        buttons.addWidget(stop)
        buttons.addWidget(import_btn)
        root.addLayout(buttons)

        self.status = QLabel("Ready")
        self.status.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
        root.addWidget(self.status)
        self.details = QLabel("The first question appears after the selected interval.")
        self.details.setWordWrap(True)
        root.addWidget(self.details)

        root.addWidget(QLabel("Question sets"))
        self.list_widget = QListWidget()
        self.refresh_subjects()
        root.addWidget(self.list_widget, 1)

    def refresh_subjects(self):
        self.list_widget.clear()
        for name, items in self.questions.items():
            count = len(items) if isinstance(items, list) else 0
            self.list_widget.addItem(f"{name} — {count} questions")

    def start_lock(self):
        pool = self.questions.get(self.subject.currentText(), [])
        if not isinstance(pool, list) or not pool:
            QMessageBox.warning(self, APP_NAME, "This question set has no questions.")
            return
        self.locked = True
        self.remaining = self.interval.value() * 60
        self.target_process_name = normalize(self.game.text())
        self.status.setText("RUNNING — game time earned")
        self.details.setText(
            "StudyLock monitors the foreground Windows app externally. "
            "It does not inject into or modify games."
        )

    def stop_lock(self):
        self.locked = False
        self.current_question = None
        if self.overlay:
            self.overlay._unlocking = True
            self.overlay.close()
            self.overlay = None
        self.status.setText("Stopped")
        self.details.setText("Ready")

    def tick(self):
        if not self.locked or self.current_question:
            return
        proc = foreground_process()
        if self.target_process_name and proc:
            name = normalize(proc.name())
            target = self.target_process_name
            if target not in name and name not in target:
                return
        elif self.target_process_name and not proc:
            return

        self.remaining -= 1
        if self.remaining <= 0:
            self.show_question()
        else:
            mins, secs = divmod(self.remaining, 60)
            self.status.setText(f"RUNNING — next question in {mins:02d}:{secs:02d}")

    def show_question(self):
        pool = self.questions.get(self.subject.currentText(), [])
        if not isinstance(pool, list) or not pool:
            self.stop_lock()
            return

        # Deterministic rotation avoids repeated random state and is lightweight.
        index = int(time.time()) % len(pool)
        self.current_question = pool[index]
        self.overlay = QuestionOverlay(self.current_question, self.question_finished)
        self.overlay._unlocking = False
        self.overlay.show()
        self.status.setText("LOCKED — answer the question to continue")

    def keep_overlay_foreground(self):
        if self.overlay and self.overlay.isVisible():
            self.overlay.force_foreground()

    def question_finished(self, correct):
        if not correct:
            return
        self.remaining = self.interval.value() * 60
        self.current_question = None
        if self.overlay:
            self.overlay._unlocking = True
            self.overlay.close()
            self.overlay = None
        self.status.setText("Correct! Game time unlocked.")

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import question sets", "", "JSON files (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Root must be an object of subject names to question arrays.")
            for subject, questions in data.items():
                if not isinstance(subject, str) or not isinstance(questions, list):
                    raise ValueError("Each subject must contain a question array.")
                for item in questions:
                    if not isinstance(item, dict) or not item.get("question") or not isinstance(item.get("answers"), list):
                        raise ValueError("Each question needs 'question' text and an 'answers' array.")
            self.questions = data
            save_questions(data)
            self.subject.clear()
            self.subject.addItems(sorted(self.questions.keys()))
            self.refresh_subjects()
            QMessageBox.information(self, APP_NAME, "Question sets imported.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Could not import questions:\n{exc}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = StudyLock()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
