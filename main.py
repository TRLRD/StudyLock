import ctypes
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import psutil
from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget
)

from curriculum import available_curricula, filter_questions, papers_for, stages_for, subjects_for
from sample_questions import questions as bundled_questions

APP_NAME = "StudyLock"
DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUESTIONS_FILE = DATA_DIR / "questions.json"
STATS_FILE = DATA_DIR / "stats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_TIMER = {"size": 18, "color": "#ffffff", "corner": "top-right", "resolution": "auto"}
DEFAULT_SETTINGS = {"game": {}, "interval": 20, "timer": DEFAULT_TIMER, "reduced_motion": False}


def norm(v: Any) -> str:
    return " ".join(str(v).strip().lower().replace("²", "2").replace("³", "3").replace("−", "-").replace("×", "x").split())


def atomic_write(path: Path, value: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def validate_questions(data: Any) -> list[dict]:
    data = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(data, list):
        raise ValueError("Question data must be a list.")
    curricula = {c.id: c for c in available_curricula()}
    out, ids = [], set()
    for i, q in enumerate(data, 1):
        if not isinstance(q, dict) or not str(q.get("question", "")).strip() or not isinstance(q.get("answers"), list) or not q["answers"]:
            raise ValueError(f"Question {i} is invalid.")
        cid = norm(q.get("curriculum", "gcse"))
        subject = str(q.get("subject", "Chemistry"))
        stage = str(q.get("qualification_stage", "A Level"))
        if cid not in curricula or subject not in curricula[cid].subjects or stage not in curricula[cid].qualification_stages:
            raise ValueError(f"Question {i}: course metadata is invalid.")
        qid = str(q.get("id") or f"q-{i}")
        if qid in ids:
            raise ValueError(f"Duplicate question id: {qid}")
        ids.add(qid)
        out.append({
            **q,
            "id": qid,
            "question": str(q["question"]),
            "choices": [str(x) for x in q.get("choices", [])],
            "answers": [str(x) for x in q["answers"]],
            "topic": str(q.get("topic") or "General"),
            "subtopic": str(q.get("subtopic") or ""),
            "difficulty": str(q.get("difficulty") or "Normal"),
            "curriculum": cid,
            "subject": subject,
            "qualification_stage": stage,
            "paper": str(q.get("paper") or "all"),
            "numeric_tolerance": max(0.0, float(q.get("numeric_tolerance", 0))),
            "exam_board": str(q.get("exam_board") or ""),
            "paper_reference": str(q.get("paper_reference") or ""),
            "year": str(q.get("year") or ""),
            "session": str(q.get("session") or ""),
            "source": str(q.get("source") or "original"),
        })
    return out


def ensure_questions() -> list[dict]:
    seed = bundled_questions()
    data = load_json(QUESTIONS_FILE, None)
    if data is None:
        atomic_write(QUESTIONS_FILE, {"questions": seed})
        return seed
    try:
        return validate_questions(data)
    except Exception:
        return seed


def load_stats() -> dict:
    default = {"questions": {}, "sessions": 0, "total_answered": 0, "total_correct": 0}
    value = load_json(STATS_FILE, default)
    return value if isinstance(value, dict) else default


def save_stats(stats: dict) -> None:
    atomic_write(STATS_FILE, stats)


def load_settings() -> dict:
    value = load_json(SETTINGS_FILE, {})
    value = value if isinstance(value, dict) else {}
    for key, default in DEFAULT_SETTINGS.items():
        value.setdefault(key, default.copy() if isinstance(default, dict) else default)
    value["timer"] = {**DEFAULT_TIMER, **(value.get("timer") or {})}
    return value


def save_settings(settings: dict) -> None:
    atomic_write(SETTINGS_FILE, settings)


def foreground() -> tuple[int, int]:
    if sys.platform != "win32":
        return 0, 0
    try:
        hwnd = int(ctypes.windll.user32.GetForegroundWindow())
        pid = ctypes.c_ulong(0)
        if not hwnd:
            return 0, 0
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return hwnd, int(pid.value)
    except Exception:
        return 0, 0


def window_rect(hwnd: int) -> QRect | None:
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        class R(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
        r = R()
        if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return QRect(r.l, r.t, r.r - r.l, r.b - r.t)
    except Exception:
        pass
    return None


def topmost(hwnd: int) -> None:
    if sys.platform == "win32" and hwnd:
        try:
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)
        except Exception:
            pass


STYLE = """
QWidget { background:#090d13; color:#eef2f7; font-family:'Segoe UI'; font-size:14px; }
QMainWindow { background:#070a0f; }
QFrame#card { background:#101722; border:1px solid #202b3a; border-radius:16px; }
QLabel#title { font-size:30px; font-weight:700; letter-spacing:1px; }
QLabel#section { color:#aeb8c7; font-size:12px; font-weight:700; letter-spacing:1px; }
QLabel#muted { color:#8793a5; }
QLabel#status { background:#13241b; color:#6fe0a2; border:1px solid #214e37; border-radius:11px; padding:6px 11px; font-weight:700; }
QLineEdit, QComboBox, QSpinBox { background:#0c121b; border:1px solid #293548; border-radius:10px; padding:10px; color:#eef2f7; min-height:20px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border:1px solid #647dff; }
QComboBox QAbstractItemView { background:#101722; border:1px solid #334158; selection-background-color:#4259a8; padding:4px; }
QPushButton { background:#151f2d; border:1px solid #2a394d; border-radius:11px; padding:10px 15px; font-weight:650; }
QPushButton:hover { background:#263651; border-color:#6c82ff; }
QPushButton:pressed { background:#526bd1; border-color:#8295ff; padding-top:12px; padding-bottom:8px; }
QPushButton#primary { background:#536df3; border:1px solid #7187ff; color:white; padding:12px 20px; }
QPushButton#primary:hover { background:#6a82ff; }
QPushButton#primary:pressed { background:#3f58c8; padding-top:14px; padding-bottom:10px; }
QTableWidget { background:#0c121b; border:1px solid #202b3a; border-radius:10px; gridline-color:#202b3a; }
QHeaderView::section { background:#151e2b; padding:9px; border:0; font-weight:700; }
"""


class GamePicker(QDialog):
    def __init__(self, parent=None, selected=None):
        super().__init__(parent)
        self.setWindowTitle("Select game")
        self.resize(760, 540)
        self.selected = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel("Choose the Windows game/app StudyLock should monitor. Other apps stay usable."))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search application…")
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Application", "PID", "Executable"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.populate)
        row.addWidget(refresh)
        row.addStretch()
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept_choice)
        box.rejected.connect(self.reject)
        row.addWidget(box)
        layout.addLayout(row)
        self.search.textChanged.connect(self.populate)
        self.populate()
        self.preselect(selected or {})

    def populate(self):
        query = norm(self.search.text())
        self.table.setRowCount(0)
        seen = set()
        for process in psutil.process_iter(["pid", "name", "exe"]):
            try:
                name = process.info.get("name") or ""
                exe = Path(process.info.get("exe") or name).name
                pid = int(process.info["pid"])
                key = (norm(name), norm(exe))
                if not name or key in seen or (query and query not in norm(name) and query not in norm(exe)):
                    continue
                seen.add(key)
                row = self.table.rowCount()
                self.table.insertRow(row)
                for col, value in enumerate((name, pid, exe)):
                    self.table.setItem(row, col, QTableWidgetItem(str(value)))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                continue

    def preselect(self, selected):
        for row in range(self.table.rowCount()):
            if selected.get("exe") and norm(self.table.item(row, 2).text()) == norm(selected["exe"]):
                self.table.selectRow(row)
                return

    def accept_choice(self):
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


class TimerSettings(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer settings")
        self.settings = settings
        layout = QVBoxLayout(self)
        form = QFormLayout()
        timer = settings["timer"]
        self.size = QSpinBox(); self.size.setRange(10, 72); self.size.setValue(int(timer["size"])); self.size.setSuffix(" px")
        self.corner = QComboBox(); self.corner.addItems(["top-left", "top-right", "bottom-left", "bottom-right"]); self.corner.setCurrentText(timer["corner"])
        self.resolution = QComboBox(); self.resolution.addItems(["Auto (display)", "1920x1080", "1600x900", "1366x768", "1280x720"])
        self.resolution.setCurrentText("Auto (display)" if timer["resolution"] == "auto" else timer["resolution"])
        self.color = QPushButton(timer["color"]); self.color.clicked.connect(self.pick_color)
        form.addRow("Timer size", self.size); form.addRow("Timer position", self.corner); form.addRow("Question resolution", self.resolution); form.addRow("Timer color", self.color)
        layout.addLayout(form)
        hint = QLabel("Auto uses the physical display containing the selected game. 1920×1080 is supported explicitly.")
        hint.setObjectName("muted"); hint.setWordWrap(True); layout.addWidget(hint)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.save); box.rejected.connect(self.reject); layout.addWidget(box)

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color.text()), self)
        if color.isValid(): self.color.setText(color.name())

    def save(self):
        self.settings["timer"] = {
            "size": self.size.value(),
            "corner": self.corner.currentText(),
            "resolution": "auto" if self.resolution.currentText().startswith("Auto") else self.resolution.currentText(),
            "color": self.color.text(),
        }
        self.accept()


class TimerHUD(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.last_second = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self); layout.setContentsMargins(7, 4, 7, 4)
        self.label = QLabel("00:00"); self.label.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(self.label)
        self.pulse = QPropertyAnimation(self.label, b"windowOpacity", self)
        self.pulse.setDuration(420); self.pulse.setStartValue(1.0); self.pulse.setEndValue(0.32); self.pulse.setEasingCurve(QEasingCurve.Type.InOutSine); self.pulse.setLoopCount(2)
        self.apply()

    def apply(self):
        timer = self.settings["timer"]
        self.label.setFont(QFont("Segoe UI", int(timer["size"]), QFont.Weight.Bold))
        self.normal = f"color:{timer['color']};background:rgba(10,14,21,225);border:1px solid rgba(255,255,255,45);border-radius:10px;padding:5px 10px;"
        self.alert = "color:#ff5365;background:rgba(24,10,14,232);border:1px solid rgba(255,83,101,150);border-radius:10px;padding:5px 10px;"
        self.label.setStyleSheet(self.normal)

    def update_time(self, seconds, screen):
        seconds = max(0, int(seconds))
        self.label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")
        self.adjustSize()
        g = screen.geometry(); margin = 18; corner = self.settings["timer"]["corner"]
        x = g.left() + margin if "left" in corner else g.right() - self.width() - margin + 1
        y = g.top() + margin if "top" in corner else g.bottom() - self.height() - margin + 1
        self.move(x, y)
        if 0 < seconds <= 5:
            self.label.setStyleSheet(self.alert)
            if self.last_second != seconds:
                self.last_second = seconds; self.pulse.stop(); self.pulse.start()
        else:
            self.last_second = None; self.pulse.stop(); self.label.setWindowOpacity(1); self.label.setStyleSheet(self.normal)


class LockChain(QWidget):
    """Full-display lock animation: four locks travel from the exact center to the four corners."""
    def __init__(self, geometry, reduced=False):
        super().__init__()
        self.setGeometry(geometry)
        self.reduced = reduced
        self.progress = 0.0
        self.timer = QTimer(self); self.timer.timeout.connect(self.step)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def start(self):
        self.progress = 0.0; self.show(); self.raise_()
        if self.reduced:
            self.progress = 1.0; self.update(); QTimer.singleShot(160, self.finish)
        else:
            self.timer.start(16)

    def step(self):
        self.progress = min(1.0, self.progress + 0.026)
        self.update()
        if self.progress >= 1.0:
            self.timer.stop(); QTimer.singleShot(170, self.finish)

    def finish(self):
        self.hide(); self.deleteLater()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height(); center = QPointF(w / 2, h / 2)
        inset = 38
        corners = [QPointF(inset, inset), QPointF(w - inset, inset), QPointF(inset, h - inset), QPointF(w - inset, h - inset)]
        # A subtle dark veil keeps the game visible while the lock mechanism is readable.
        p.fillRect(self.rect(), QColor(7, 10, 15, 70))
        eased = 1 - (1 - self.progress) ** 3
        for corner in corners:
            point = QPointF(center.x() + (corner.x() - center.x()) * eased, center.y() + (corner.y() - center.y()) * eased)
            p.setPen(QPen(QColor(103, 126, 255, 185), 3)); p.drawLine(center, point)
            # chain links
            if eased > 0.05:
                dx, dy = point.x() - center.x(), point.y() - center.y(); length = max(1.0, (dx * dx + dy * dy) ** 0.5)
                ux, uy = dx / length, dy / length
                for dist in range(45, int(length), 34):
                    x, y = center.x() + ux * dist, center.y() + uy * dist
                    p.setPen(QPen(QColor(160, 175, 220, 125), 2)); p.drawEllipse(int(x - 5), int(y - 5), 10, 10)
            self.draw_lock(p, point, 0.95 if eased > 0.15 else eased * 5)
        p.setPen(QPen(QColor(255,255,255,60), 1)); p.drawEllipse(int(center.x()-28), int(center.y()-28), 56, 56)

    @staticmethod
    def draw_lock(p, point, opacity):
        alpha = max(20, min(235, int(235 * opacity))); x, y = int(point.x()), int(point.y())
        p.setBrush(QBrush(QColor(16, 23, 35, alpha))); p.setPen(QPen(QColor(120, 143, 255, alpha), 2))
        p.drawRoundedRect(x - 21, y - 15, 42, 34, 9, 9)
        p.setPen(QPen(QColor(235, 240, 250, alpha), 3)); p.drawArc(x - 9, y - 18, 18, 22, 0, 180 * 16); p.drawRect(x - 8, y - 2, 16, 13)


class AnswerButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(58); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("""
        QPushButton { background:rgba(21,29,43,242); border:1px solid rgba(128,146,181,75); border-radius:14px; padding:10px 18px; text-align:left; font-size:16px; }
        QPushButton:hover { background:rgba(72,91,139,248); border:1px solid rgba(145,164,255,225); padding-left:22px; }
        QPushButton:pressed { background:rgba(92,118,232,255); border:1px solid #a5b3ff; padding-left:27px; padding-top:12px; }
        """)


class Overlay(QWidget):
    def __init__(self, question, answer_callback, target_callback, settings):
        super().__init__()
        self.question = question; self.answer_callback = answer_callback; self.target_callback = target_callback; self.settings = settings
        self.allow_close = False; self.started = time.monotonic(); self.hwnd = 0
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self); layout.setContentsMargins(70, 60, 70, 60); layout.setSpacing(16)
        title = QLabel("STUDYLOCK  •  ANSWER TO CONTINUE"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setFont(QFont("Segoe UI", 21, QFont.Weight.Bold)); layout.addWidget(title)
        meta = f"{question.get('topic','General')}  •  {question.get('difficulty','Normal')}"
        if question.get("paper") not in (None, "", "all"): meta += f"  •  {question.get('paper')}"
        meta_label = QLabel(meta); meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter); meta_label.setObjectName("muted"); layout.addWidget(meta_label)
        prompt = QLabel(question["question"]); prompt.setWordWrap(True); prompt.setAlignment(Qt.AlignmentFlag.AlignCenter); prompt.setFont(QFont("Segoe UI", 25, QFont.Weight.DemiBold)); layout.addWidget(prompt, 1)
        choices = question.get("choices", [])
        if choices:
            for index, choice in enumerate(choices):
                button = AnswerButton(f"{chr(65 + index)}   {choice}"); button.clicked.connect(lambda _, value=choice: self.submit(value)); layout.addWidget(button)
        else:
            self.input = QLineEdit(); self.input.setPlaceholderText("Type your answer…"); self.input.setMinimumHeight(56); self.input.returnPressed.connect(lambda: self.submit(self.input.text())); layout.addWidget(self.input)
            button = AnswerButton("CHECK ANSWER"); button.setObjectName("primary"); button.clicked.connect(lambda: self.submit(self.input.text())); layout.addWidget(button)
        self.fade = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.fade); self.fade_anim = QPropertyAnimation(self.fade, b"opacity", self); self.fade_anim.setDuration(360); self.fade_anim.setStartValue(0); self.fade_anim.setEndValue(1); self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.reveal_anim = None
        self.watchdog = QTimer(self); self.watchdog.timeout.connect(self.watch_target); self.watchdog.start(120)

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Exactly 25% opacity backdrop: game remains clearly visible underneath.
        painter.fillRect(self.rect(), QColor(7, 10, 15, 64))
        card = self.rect().adjusted(35, 35, -35, -35)
        painter.setBrush(QBrush(QColor(15, 21, 31, 246))); painter.setPen(QPen(QColor(103, 125, 170, 105), 1)); painter.drawRoundedRect(card, 22, 22)

    def showEvent(self, event):
        super().showEvent(event); self.hwnd = int(self.winId()); self.place(); self.animate_rise(); self.watch_target()

    def place(self):
        hwnd, _ = self.target_callback(); rect = window_rect(hwnd) if hwnd else None
        screen = QApplication.screenAt(rect.center()) if rect else QApplication.primaryScreen(); screen = screen or QApplication.primaryScreen(); geometry = screen.geometry()
        selected = self.settings["timer"]["resolution"]
        if selected != "auto":
            try:
                width, height = map(int, selected.split("x")); width = min(width, geometry.width()); height = min(height, geometry.height())
                self.setGeometry(geometry.x() + (geometry.width() - width)//2, geometry.y() + (geometry.height() - height)//2, width, height); return
            except Exception: pass
        self.setGeometry(geometry)

    def animate_rise(self):
        if self.settings.get("reduced_motion"):
            self.fade_anim.start(); return
        final = self.geometry(); start = QRect(final.x(), final.y() + min(80, final.height() // 10), final.width(), final.height())
        self.setGeometry(start); self.fade_anim.start()
        self.reveal_anim = QPropertyAnimation(self, b"geometry", self); self.reveal_anim.setDuration(520); self.reveal_anim.setStartValue(start); self.reveal_anim.setEndValue(final); self.reveal_anim.setEasingCurve(QEasingCurve.Type.OutCubic); self.reveal_anim.start()

    def watch_target(self):
        hwnd, pid = self.target_callback(); foreground_hwnd, foreground_pid = foreground()
        if self.hwnd and foreground_hwnd == self.hwnd: return
        if hwnd and foreground_pid == pid:
            self.place(); topmost(self.hwnd); self.show()
        elif self.isVisible(): self.hide()

    def submit(self, value):
        elapsed = max(0.05, time.monotonic() - self.started); self.allow_close = True; self.answer_callback(value, elapsed); self.close()

    def closeEvent(self, event):
        if self.allow_close: event.accept()
        else: event.ignore()


class PerformanceDialog(QDialog):
    def __init__(self, stats, weak_only=False, parent=None):
        super().__init__(parent); self.setWindowTitle("StudyLock Performance"); self.resize(980, 620)
        layout = QVBoxLayout(self); title = QLabel("Topic performance"); title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold)); layout.addWidget(title)
        info = QLabel("Accuracy is the primary signal. Speed is secondary, so rushing wrong answers does not create fake mastery."); info.setObjectName("muted"); layout.addWidget(info)
        topics = {}
        for record in stats.get("questions", {}).values():
            topic = record.get("topic", "General"); item = topics.setdefault(topic, {"attempts":0,"correct":0,"wrong":0,"times":[]})
            item["attempts"] += int(record.get("attempts", 0)); item["correct"] += int(record.get("correct", 0)); item["wrong"] += int(record.get("wrong", 0)); item["times"] += list(record.get("times", []))
        table = QTableWidget(0, 6); table.setHorizontalHeaderLabels(["Topic","Accuracy","Avg time","Wrong","Mastery","Recommendation"]); table.horizontalHeader().setStretchLastSection(True); layout.addWidget(table, 1)
        for topic, item in sorted(topics.items()):
            accuracy = item["correct"] / item["attempts"] * 100 if item["attempts"] else 0
            average = sum(item["times"]) / len(item["times"]) if item["times"] else 0
            mastery = round(accuracy * .8 + max(0, min(100, 100 - average * 3)) * .2)
            recommendation = "Strong" if mastery >= 85 else "Maintain" if mastery >= 70 else "Practice soon" if mastery >= 55 else "Weak point — prioritize practice"
            if weak_only and mastery >= 70: continue
            values = [topic, f"{accuracy:.0f}%", f"{average:.1f}s", str(item["wrong"]), f"{mastery}/100", recommendation]
            row = table.rowCount(); table.insertRow(row)
            for col, value in enumerate(values): table.setItem(row, col, QTableWidgetItem(str(value)))
        close = QPushButton("Close"); close.clicked.connect(self.accept); layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_NAME); self.resize(1040, 760); self.setMinimumSize(900, 680); self.setStyleSheet(STYLE)
        self.questions = ensure_questions(); self.stats = load_stats(); self.settings = load_settings(); self.recent = []; self.current = None; self.overlay = None; self.lock_anim = None; self.running = False; self.next_at = 0
        self.tick = QTimer(self); self.tick.setInterval(250); self.tick.timeout.connect(self.loop)
        self.build_ui(); self.refresh_course(); self.refresh_status(); self.refresh_game_label()

    def card(self):
        frame = QFrame(); frame.setObjectName("card"); return frame

    def build_ui(self):
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(32, 28, 32, 28); outer.setSpacing(18)
        header = QHBoxLayout();
        title_box = QVBoxLayout(); title = QLabel(APP_NAME); title.setObjectName("title"); title_box.addWidget(title); subtitle = QLabel("Focused study without leaving your game."); subtitle.setObjectName("muted"); title_box.addWidget(subtitle); header.addLayout(title_box); header.addStretch()
        self.status = QLabel("STOPPED"); self.status.setObjectName("status"); header.addWidget(self.status, 0, Qt.AlignmentFlag.AlignTop); outer.addLayout(header)

        course = self.card(); grid = QGridLayout(course); grid.setContentsMargins(22, 20, 22, 22); grid.setHorizontalSpacing(14); grid.setVerticalSpacing(9)
        self.curr = QComboBox(); self.curr.addItems([c.name for c in available_curricula()]); self.curr.currentIndexChanged.connect(self.refresh_course)
        self.subj = QComboBox(); self.subj.currentIndexChanged.connect(self.refresh_qualification)
        self.qual = QComboBox(); self.qual.currentIndexChanged.connect(self.refresh_papers)
        self.paper = QComboBox(); self.paper.currentIndexChanged.connect(self.refresh_status)
        for col, label, widget in [(0,"CURRICULUM",self.curr),(1,"SUBJECT",self.subj),(2,"QUALIFICATION",self.qual),(3,"PAPER",self.paper)]:
            lab = QLabel(label); lab.setObjectName("section"); grid.addWidget(lab,0,col); grid.addWidget(widget,1,col)
        outer.addWidget(course)

        game = self.card(); row = QHBoxLayout(game); row.setContentsMargins(22, 18, 22, 18); game_text = QVBoxLayout(); gl = QLabel("TARGET APPLICATION"); gl.setObjectName("section"); game_text.addWidget(gl); self.game_label = QLabel("No game selected"); self.game_label.setObjectName("muted"); game_text.addWidget(self.game_label); row.addLayout(game_text,1); select = QPushButton("Select game"); select.clicked.connect(self.pick_game); row.addWidget(select); outer.addWidget(game)

        controls = self.card(); row = QHBoxLayout(controls); row.setContentsMargins(22, 18, 22, 18); label = QLabel("Question interval"); label.setObjectName("muted"); row.addWidget(label); self.interval = QSpinBox(); self.interval.setRange(5,3600); self.interval.setValue(int(self.settings.get("interval",20))); self.interval.setSuffix(" sec"); row.addWidget(self.interval); row.addStretch()
        timer_button = QPushButton("Timer settings"); timer_button.clicked.connect(self.timer_settings); row.addWidget(timer_button); performance = QPushButton("Performance"); performance.clicked.connect(lambda: self.show_perf(False)); row.addWidget(performance); weak = QPushButton("Practice weak areas"); weak.clicked.connect(lambda: self.show_perf(True)); row.addWidget(weak); outer.addWidget(controls)

        actions = QHBoxLayout(); self.start_button = QPushButton("START STUDYLOCK"); self.start_button.setObjectName("primary"); self.start_button.setMinimumWidth(190); self.start_button.clicked.connect(self.toggle); actions.addWidget(self.start_button); stop_button = QPushButton("STOP"); stop_button.setMinimumWidth(90); stop_button.clicked.connect(self.stop); actions.addWidget(stop_button); actions.addStretch(); imp = QPushButton("Import question bank"); imp.clicked.connect(self.import_questions); actions.addWidget(imp); exp = QPushButton("Export question bank"); exp.clicked.connect(self.export_questions); actions.addWidget(exp); outer.addLayout(actions)

        info = self.card(); info_layout = QVBoxLayout(info); info_layout.setContentsMargins(22,18,22,18); note = QLabel("StudyLock only interrupts the selected game. Switching to another app hides the question; returning to the selected game shows it again."); note.setWordWrap(True); info_layout.addWidget(note); self.bank_label = QLabel(); self.bank_label.setObjectName("muted"); info_layout.addWidget(self.bank_label); outer.addWidget(info); outer.addStretch(); self.setCentralWidget(root)

    def refresh_course(self):
        curricula = available_curricula();
        if not curricula: return
        curriculum = curricula[self.curr.currentIndex()]; subjects = subjects_for(curriculum.id); old = self.subj.currentText(); self.subj.blockSignals(True); self.subj.clear(); self.subj.addItems(subjects); self.subj.setCurrentText(old if old in subjects else (subjects[0] if subjects else "")); self.subj.blockSignals(False); self.refresh_qualification()

    def refresh_qualification(self):
        curriculum = available_curricula()[self.curr.currentIndex()]; stages = stages_for(curriculum.id); old = self.qual.currentText(); self.qual.blockSignals(True); self.qual.clear(); self.qual.addItems(stages); self.qual.setCurrentText(old if old in stages else (stages[0] if stages else "")); self.qual.blockSignals(False); self.refresh_papers()

    def refresh_papers(self):
        curriculum = available_curricula()[self.curr.currentIndex()]; papers = papers_for(curriculum.id, self.subj.currentText(), self.qual.currentText()); self.paper.blockSignals(True); self.paper.clear(); self.paper.addItem("All papers", "all")
        for paper in papers: self.paper.addItem(f"{paper.name} — {paper.description}", paper.id)
        self.paper.blockSignals(False); self.refresh_status()

    def selected_filter(self):
        curriculum = available_curricula()[self.curr.currentIndex()]; return curriculum.id, self.subj.currentText(), self.qual.currentText(), self.paper.currentData() or "all"

    def refresh_status(self):
        if not hasattr(self, "bank_label"): return
        cid, subject, stage, paper = self.selected_filter(); questions = filter_questions(self.questions, curriculum_id=cid, subject=subject, qualification_stage=stage, paper_id=paper); self.bank_label.setText(f"{len(questions)} questions available  •  {self.stats.get('total_answered',0)} answers recorded")

    def refresh_game_label(self):
        game = self.settings.get("game") or {}; self.game_label.setText(f"{game.get('name','No game selected')}  •  PID {game.get('pid')}" if game else "No game selected")

    def pick_game(self):
        dialog = GamePicker(self, self.settings.get("game", {}));
        if dialog.exec(): self.settings["game"] = dialog.selected; save_settings(self.settings); self.refresh_game_label()

    def timer_settings(self):
        dialog = TimerSettings(self.settings, self)
        if dialog.exec(): save_settings(self.settings); self.settings = load_settings()

    def show_perf(self, weak): PerformanceDialog(self.stats, weak, self).exec()

    def choose_question(self):
        cid, subject, stage, paper = self.selected_filter(); questions = filter_questions(self.questions, curriculum_id=cid, subject=subject, qualification_stage=stage, paper_id=paper)
        if not questions: return None
        pool = [q for q in questions if q.get("id") not in self.recent] or questions
        def weight(question):
            record = self.stats.get("questions", {}).get(question.get("id"), {}); attempts = int(record.get("attempts", 0)); accuracy = int(record.get("correct", 0)) / attempts if attempts else .5; return 1.8 - accuracy
        question = random.choices(pool, weights=[weight(q) for q in pool], k=1)[0]; self.recent = (self.recent + [question.get("id")])[-12:]; return question

    def answer(self, value, elapsed):
        question = self.current
        if not question: return False
        correct = norm(value) in {norm(a) for a in question.get("answers", [])}
        if not correct and question.get("numeric_tolerance", 0) > 0:
            try: correct = any(abs(float(norm(value)) - float(a)) <= question["numeric_tolerance"] for a in question.get("answers", []))
            except Exception: pass
        record = self.stats.setdefault("questions", {}).setdefault(question["id"], {"attempts":0,"correct":0,"wrong":0,"times":[],"topic":question.get("topic","General")}); record["attempts"] += 1; record["times"].append(round(elapsed,2)); self.stats["total_answered"] = self.stats.get("total_answered",0) + 1
        if correct: record["correct"] += 1; self.stats["total_correct"] = self.stats.get("total_correct",0) + 1
        else: record["wrong"] += 1
        save_stats(self.stats); self.current = None; self.refresh_status(); return correct

    def target(self):
        game = self.settings.get("game") or {}; hwnd, pid = foreground();
        if not hwnd: return 0, 0
        if game.get("pid") and pid == int(game["pid"]): return hwnd, pid
        try:
            if game.get("exe") and norm(psutil.Process(pid).name()) == norm(game["exe"]): return hwnd, pid
        except psutil.Error: pass
        return 0, 0

    def trigger_question(self):
        if not self.running: return
        question = self.choose_question()
        if not question: return
        self.current = question; self.overlay = Overlay(question, self.answer, self.target, self.settings); self.overlay.show()

    def trigger_with_animation(self):
        hwnd, _ = self.target(); rect = window_rect(hwnd) if hwnd else None; screen = QApplication.screenAt(rect.center()) if rect else QApplication.primaryScreen(); screen = screen or QApplication.primaryScreen(); geometry = screen.geometry()
        self.lock_anim = LockChain(geometry, bool(self.settings.get("reduced_motion"))); self.lock_anim.start(); QTimer.singleShot(720 if not self.settings.get("reduced_motion") else 190, self.trigger_question)

    def start_run(self):
        if not self.settings.get("game"): QMessageBox.warning(self, APP_NAME, "Select a game first."); return
        cid, subject, stage, paper = self.selected_filter(); available = filter_questions(self.questions, curriculum_id=cid, subject=subject, qualification_stage=stage, paper_id=paper)
        if not available: QMessageBox.warning(self, APP_NAME, "No questions match the current curriculum, subject, qualification, and paper selection."); return
        self.running = True; self.next_at = time.monotonic() + self.interval.value(); self.start_button.setText("STOP STUDYLOCK"); self.status.setText("RUNNING"); self.status.setStyleSheet("background:#13241b;color:#6fe0a2;border:1px solid #214e37;border-radius:11px;padding:6px 11px;font-weight:700;"); self.hud = TimerHUD(self.settings); self.hud.show(); self.tick.start()

    def toggle(self): self.stop() if self.running else self.start_run()

    def stop(self):
        self.running = False; self.tick.stop()
        if hasattr(self, "hud"): self.hud.close()
        if self.overlay: self.overlay.allow_close = True; self.overlay.close(); self.overlay = None
        self.current = None; self.status.setText("STOPPED"); self.start_button.setText("START STUDYLOCK")

    def loop(self):
        if not self.running: return
        hwnd, pid = self.target();
        if not hwnd or not pid: return
        rect = window_rect(hwnd); screen = QApplication.screenAt(rect.center()) if rect else QApplication.primaryScreen(); screen = screen or QApplication.primaryScreen()
        if hasattr(self, "hud"): self.hud.update_time(max(0, self.next_at - time.monotonic()), screen)
        if time.monotonic() >= self.next_at:
            self.next_at = time.monotonic() + self.interval.value()
            if self.overlay is None or not self.overlay.isVisible(): self.trigger_with_animation()

    def import_questions(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import question bank", "", "JSON files (*.json)")
        if not path: return
        try:
            parsed = validate_questions(json.loads(Path(path).read_text(encoding="utf-8"))); self.questions = parsed; atomic_write(QUESTIONS_FILE, {"questions": parsed}); self.refresh_status(); QMessageBox.information(self, APP_NAME, f"Imported {len(parsed)} questions.")
        except Exception as exc: QMessageBox.critical(self, APP_NAME, f"Import failed:\n{exc}")

    def export_questions(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export question bank", "studylock_questions.json", "JSON files (*.json)")
        if path: Path(path).write_text(json.dumps({"questions": self.questions}, indent=2, ensure_ascii=False), encoding="utf-8")

    def closeEvent(self, event): self.stop(); event.accept()


def main():
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); window = MainWindow(); window.show(); sys.exit(app.exec())


if __name__ == "__main__":
    main()
