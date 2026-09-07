import json, os, random, sys, time, ctypes
from pathlib import Path
from typing import Any

import psutil
from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtGui import QFont, QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget
)
from curriculum import available_curricula, filter_questions

APP_NAME = "StudyLock"
DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / APP_NAME
DATA_DIR.mkdir(parents=True, exist_ok=True)
QUESTIONS_FILE = DATA_DIR / "questions.json"
STATS_FILE = DATA_DIR / "stats.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

# Original test questions only. Official past-paper text is not bundled.
SEED_QUESTIONS = [
    {"id":"al-001","question":"Which species is oxidised when magnesium reacts with hydrochloric acid?","choices":["Mg","H+","Cl−","H2"],"answers":["Mg"],"topic":"Redox","difficulty":"Easy"},
    {"id":"al-002","question":"What is the oxidation number of sulfur in SO4^2−?","choices":["+2","+4","+6","−2"],"answers":["+6","6"],"topic":"Oxidation numbers","difficulty":"Easy"},
    {"id":"al-003","question":"Which type of bonding is present between atoms in a giant covalent structure?","choices":["Metallic","Ionic","Covalent","Hydrogen bonding"],"answers":["Covalent"],"topic":"Bonding","difficulty":"Easy"},
    {"id":"al-004","question":"For a gaseous equilibrium, what happens when pressure is increased if the product side has fewer moles of gas?","choices":["It moves to products","It moves to reactants","It does not change","The reaction stops"],"answers":["It moves to products"],"topic":"Equilibria","difficulty":"Normal"},
    {"id":"al-005","question":"What is the formula of the conjugate base formed when NH4+ donates a proton?","choices":["NH3","NH2−","NH4OH","N2H4"],"answers":["NH3"],"topic":"Acids and bases","difficulty":"Easy"},
    {"id":"al-006","question":"A reaction has an enthalpy change of −125 kJ mol−1. Is the reaction exothermic or endothermic?","choices":["Exothermic","Endothermic"],"answers":["Exothermic"],"topic":"Energetics","difficulty":"Easy"},
    {"id":"al-007","question":"Calculate the amount of substance in 0.50 mol dm−3 solution when 0.020 dm3 is used. Give the answer in mol.","choices":[],"answers":["0.010","0.01","1.0e-2"],"topic":"Amount of substance","difficulty":"Normal","numeric_tolerance":0.0002},
    {"id":"al-008","question":"Which particle has the same number of electrons as a neutral neon atom?","choices":["Na+","Na","F−","O2−"],"answers":["Na+","F−"],"topic":"Atomic structure","difficulty":"Normal"},
]

def norm(v: Any) -> str:
    s = str(v).strip().lower().replace("²", "2").replace("³", "3").replace("−", "-").replace("×", "x")
    return " ".join(s.split())

def atomic_write(path: Path, value: Any):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

def load_json(path: Path, default: Any):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def validate_questions(data: Any) -> list[dict]:
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if not isinstance(data, list):
        raise ValueError("Question data must be a list.")
    out = []
    curriculum_ids = {c.id for c in available_curricula()}
    for i, raw in enumerate(data, 1):
        if not isinstance(raw, dict) or not str(raw.get("question", "")).strip():
            raise ValueError(f"Question {i} is invalid.")
        if not isinstance(raw.get("answers"), list) or not raw["answers"]:
            raise ValueError(f"Question {i} needs at least one accepted answer.")
        curriculum = norm(raw.get("curriculum", "gcse"))
        subject = str(raw.get("subject", "Chemistry"))
        stage = str(raw.get("qualification_stage", "A Level"))
        if curriculum not in curriculum_ids:
            raise ValueError(f"Question {i}: unknown curriculum.")
        c = next(x for x in available_curricula() if x.id == curriculum)
        if subject not in c.subjects:
            raise ValueError(f"Question {i}: subject is unavailable for this curriculum.")
        if stage not in c.qualification_stages:
            raise ValueError(f"Question {i}: qualification stage is unavailable.")
        try:
            tolerance = max(0.0, float(raw.get("numeric_tolerance", 0)))
        except (TypeError, ValueError):
            raise ValueError(f"Question {i}: numeric_tolerance must be a number.")
        choices = raw.get("choices", [])
        if not isinstance(choices, list):
            choices = []
        out.append({
            "id": str(raw.get("id") or f"q-{i}"),
            "question": str(raw["question"]),
            "choices": [str(x) for x in choices],
            "answers": [str(x) for x in raw["answers"]],
            "topic": str(raw.get("topic") or "General"),
            "difficulty": str(raw.get("difficulty") or "Normal"),
            "numeric_tolerance": tolerance,
            "curriculum": curriculum,
            "subject": subject,
            "qualification_stage": stage,
            "exam_board": str(raw.get("exam_board") or ""),
            "paper_reference": str(raw.get("paper_reference") or ""),
        })
    return out

def ensure_questions() -> list[dict]:
    data = load_json(QUESTIONS_FILE, None)
    if data is None:
        seeded = [dict(q, curriculum="gcse", subject="Chemistry", qualification_stage="A Level", exam_board="StudyLock Original") for q in SEED_QUESTIONS]
        atomic_write(QUESTIONS_FILE, {"questions": seeded})
        return seeded
    try:
        return validate_questions(data)
    except ValueError:
        try:
            QUESTIONS_FILE.rename(DATA_DIR / "questions.invalid.json")
        except OSError:
            pass
        seeded = [dict(q, curriculum="gcse", subject="Chemistry", qualification_stage="A Level", exam_board="StudyLock Original") for q in SEED_QUESTIONS]
        atomic_write(QUESTIONS_FILE, {"questions": seeded})
        return seeded

def default_stats():
    return {"questions": {}, "sessions": 0, "total_answered": 0, "total_correct": 0}

def load_stats():
    s = load_json(STATS_FILE, default_stats())
    if not isinstance(s, dict):
        s = default_stats()
    s.setdefault("questions", {}); s.setdefault("sessions", 0); s.setdefault("total_answered", 0); s.setdefault("total_correct", 0)
    return s

def save_stats(s):
    atomic_write(STATS_FILE, s)

def load_settings():
    s = load_json(SETTINGS_FILE, {"game": {}, "interval": 20})
    if not isinstance(s, dict):
        s = {"game": {}, "interval": 20}
    s.setdefault("game", {}); s.setdefault("interval", 20)
    return s

def save_settings(s):
    atomic_write(SETTINGS_FILE, s)

def process_rows():
    rows, seen = [], set()
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = p.info.get("name") or ""
            exe = Path(p.info.get("exe") or name).name
            pid = int(p.info["pid"])
            if not name or pid <= 0:
                continue
            key = (norm(exe), norm(name))
            if key in seen:
                continue
            seen.add(key); rows.append((name, pid, exe))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
            pass
    return sorted(rows, key=lambda x: norm(x[0]))

def foreground():
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

def window_rect(hwnd):
    try:
        class RECT_STRUCT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        r = RECT_STRUCT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return None
        if r.right <= r.left or r.bottom <= r.top:
            return None
        return QRect(r.left, r.top, r.right - r.left, r.bottom - r.top)
    except Exception:
        return None

def target_is_foreground(pid, exe):
    hwnd, fpid = foreground()
    if not hwnd:
        return False
    if pid and fpid == pid:
        return True
    try:
        return bool(exe) and norm(psutil.Process(fpid).name()) == norm(exe)
    except psutil.Error:
        return False

def make_topmost(hwnd):
    if sys.platform != "win32" or not hwnd:
        return
    try:
        u = ctypes.windll.user32
        u.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0040)
        u.SetForegroundWindow(hwnd)
    except Exception:
        pass

class GamePicker(QDialog):
    def __init__(self, parent=None, selected=None):
        super().__init__(parent)
        self.setWindowTitle("Select game")
        self.resize(760, 540)
        self.selected = None
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Choose the Windows game/app StudyLock should monitor. Other apps remain usable."))
        self.search = QLineEdit(); self.search.setPlaceholderText("Search by name or executable…"); v.addWidget(self.search)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Application", "PID", "Executable"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True); v.addWidget(self.table)
        row = QHBoxLayout(); refresh = QPushButton("Refresh"); refresh.clicked.connect(self.populate); row.addWidget(refresh); row.addStretch()
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept_choice); box.rejected.connect(self.reject); row.addWidget(box); v.addLayout(row)
        self.search.textChanged.connect(self.populate); self.populate(); self.preselect(selected or {})
    def populate(self):
        q = norm(self.search.text()); self.table.setRowCount(0)
        for name, pid, exe in process_rows():
            if q and q not in norm(name) and q not in norm(exe):
                continue
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(name)); self.table.setItem(r, 1, QTableWidgetItem(str(pid))); self.table.setItem(r, 2, QTableWidgetItem(exe))
    def preselect(self, s):
        target = norm(s.get("exe", ""))
        for r in range(self.table.rowCount()):
            if target and norm(self.table.item(r, 2).text()) == target:
                self.table.selectRow(r); break
    def accept_choice(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, APP_NAME, "Select a game first."); return
        r = rows[0].row(); self.selected = {"name": self.table.item(r, 0).text(), "pid": int(self.table.item(r, 1).text()), "exe": self.table.item(r, 2).text()}; self.accept()

class Overlay(QWidget):
    def __init__(self, question, on_answer, target_info):
        super().__init__()
        self.question, self.on_answer, self.target_info = question, on_answer, target_info
        self.allow_close = False; self.wrong = 0; self.started = time.monotonic(); self.overlay_hwnd = 0
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose); self.setStyleSheet("background:#111318;color:#fff;")
        v = QVBoxLayout(self); v.setContentsMargins(60, 40, 60, 40); v.setSpacing(16)
        title = QLabel("STUDYLOCK  •  ANSWER TO CONTINUE"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold)); v.addWidget(title)
        meta = QLabel(f"{question.get('topic','General')}  •  {question.get('difficulty','Normal')}"); meta.setAlignment(Qt.AlignmentFlag.AlignCenter); meta.setStyleSheet("color:#9aa0aa;"); v.addWidget(meta)
        q = QLabel(question["question"]); q.setWordWrap(True); q.setAlignment(Qt.AlignmentFlag.AlignCenter); q.setFont(QFont("Segoe UI", 25, QFont.Weight.DemiBold)); v.addWidget(q, 1)
        choices = question.get("choices", [])
        if choices:
            for c in choices:
                b = QPushButton(c); b.setMinimumHeight(48); b.clicked.connect(lambda _, x=c: self.submit(x)); v.addWidget(b)
        else:
            self.input = QLineEdit(); self.input.setPlaceholderText("Type your answer…"); self.input.setMinimumHeight(48); self.input.returnPressed.connect(lambda: self.submit(self.input.text())); v.addWidget(self.input)
            b = QPushButton("CHECK ANSWER"); b.setMinimumHeight(48); b.clicked.connect(lambda: self.submit(self.input.text())); v.addWidget(b)
        self.feedback = QLabel(""); self.feedback.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(self.feedback)
        self.watchdog = QTimer(self); self.watchdog.timeout.connect(self.watch); self.watchdog.start(120)
    def showEvent(self, event):
        super().showEvent(event); self.overlay_hwnd = int(self.winId()); self.watch()
        if hasattr(self, "input"): self.input.setFocus()
    def watch(self):
        target_hwnd, target_pid = self.target_info()
        f_hwnd, f_pid = foreground()
        # The question remains visible while it owns focus. If the user Alt+Tabs away,
        # it hides. Returning to the selected game shows it again.
        if self.overlay_hwnd and f_hwnd == self.overlay_hwnd:
            return
        if target_hwnd and f_pid == target_pid:
            r = window_rect(target_hwnd)
            if r: self.setGeometry(r)
            if not self.isVisible(): self.show()
            make_topmost(self.overlay_hwnd or int(self.winId()))
        else:
            if self.isVisible(): self.hide()
    def submit(self, value):
        elapsed = max(0.05, time.monotonic() - self.started); correct = self.on_answer(value, elapsed, self.wrong)
        if correct:
            self.allow_close = True; self.close()
        else:
            self.wrong += 1; self.feedback.setText("Incorrect — try again."); self.feedback.setStyleSheet("color:#ff8a8a;")
            if hasattr(self, "input"): self.input.selectAll(); self.input.setFocus()
            make_topmost(self.overlay_hwnd or int(self.winId()))
    def closeEvent(self, event: QCloseEvent):
        if self.allow_close: event.accept()
        else: event.ignore(); self.watch()

class PerformanceDialog(QDialog):
    def __init__(self, stats, parent=None):
        super().__init__(parent); self.setWindowTitle("Topic Performance"); self.resize(900, 540); v = QVBoxLayout(self)
        v.addWidget(QLabel("Mastery is weighted toward accuracy. Speed helps, but fast wrong answers never make a topic strong."))
        table = QTableWidget(0, 6); table.setHorizontalHeaderLabels(["Topic", "Accuracy", "Avg time", "Wrong attempts", "Mastery", "Recommendation"]); table.horizontalHeader().setStretchLastSection(True); v.addWidget(table)
        topics = {}
        for x in stats.get("questions", {}).values():
            topic = x.get("topic", "General"); a = topics.setdefault(topic, {"attempts":0,"correct":0,"wrong":0,"times":[]})
            a["attempts"] += int(x.get("attempts",0)); a["correct"] += int(x.get("correct",0)); a["wrong"] += int(x.get("wrong",0)); a["times"].extend(x.get("times", []))
        for topic, x in sorted(topics.items(), key=lambda kv: kv[0].lower()):
            acc = (x["correct"] / x["attempts"] * 100) if x["attempts"] else 0
            avg = sum(x["times"]) / len(x["times"]) if x["times"] else 0
            speed = max(0, min(100, 100 - avg * 3)); mastery = round(acc * .8 + speed * .2)
            rec = "Strong" if mastery >= 85 else "Maintain" if mastery >= 70 else "Practice soon" if mastery >= 55 else "Weak point — prioritize practice"
            vals = [topic, f"{acc:.0f}%", f"{avg:.1f}s", str(x["wrong"]), f"{mastery}/100", rec]
            r = table.rowCount(); table.insertRow(r)
            for c, val in enumerate(vals): table.setItem(r, c, QTableWidgetItem(val))
        close = QPushButton("Close"); close.clicked.connect(self.accept); v.addWidget(close)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_NAME); self.resize(900, 680)
        self.questions = ensure_questions(); self.stats = load_stats(); self.settings = load_settings()
        self.session = False; self.overlay = None; self.current = None; self.last_id = None; self.pool = []
        self.remaining = float(self.settings.get("interval",20)) * 60; self.last_tick = time.monotonic()
        self.build_ui(); self.timer = QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(250)
        self.recovery = QTimer(self); self.recovery.timeout.connect(self.recovery_hotkey); self.recovery.start(100)
    def build_ui(self):
        tabs = QTabWidget(); self.setCentralWidget(tabs)
        home = QWidget(); tabs.addTab(home, "Session"); v = QVBoxLayout(home)
        title = QLabel("StudyLock"); title.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold)); v.addWidget(title)
        v.addWidget(QLabel("Only the selected game is interrupted. Alt+Tab to other apps whenever you need to."))
        form = QFormLayout(); self.curr = QComboBox(); self.curr.addItems([c.name for c in available_curricula()]); self.curr.currentIndexChanged.connect(self.curriculum_changed); form.addRow("Curriculum", self.curr)
        self.subject = QComboBox(); form.addRow("Subject", self.subject); self.stage = QComboBox(); form.addRow("Qualification", self.stage)
        self.interval = QSpinBox(); self.interval.setRange(1, 240); self.interval.setValue(int(self.settings.get("interval",20))); self.interval.setSuffix(" minutes"); form.addRow("Question interval", self.interval); v.addLayout(form)
        row = QHBoxLayout(); self.game_label = QLabel("No game selected"); pick = QPushButton("Select Game"); pick.clicked.connect(self.pick_game); row.addWidget(self.game_label,1); row.addWidget(pick); v.addLayout(row)
        buttons = QHBoxLayout(); self.start = QPushButton("START SESSION"); self.start.clicked.connect(self.toggle_session); buttons.addWidget(self.start); perf = QPushButton("📊 Topic Performance"); perf.clicked.connect(lambda: PerformanceDialog(self.stats, self).exec()); buttons.addWidget(perf); v.addLayout(buttons)
        self.status = QLabel("Ready. Select your course and game."); self.status.setWordWrap(True); v.addWidget(self.status); v.addStretch()
        bank = QWidget(); tabs.addTab(bank, "Question Bank"); bv = QVBoxLayout(bank)
        self.qtable = QTableWidget(0, 6); self.qtable.setHorizontalHeaderLabels(["Question","Topic","Curriculum","Subject","Qualification","Answers"]); self.qtable.horizontalHeader().setStretchLastSection(True); bv.addWidget(self.qtable)
        br = QHBoxLayout(); imp = QPushButton("Import JSON"); imp.clicked.connect(self.import_questions); exp = QPushButton("Export JSON"); exp.clicked.connect(self.export_questions); br.addWidget(imp); br.addWidget(exp); br.addStretch(); bv.addLayout(br)
        self.curriculum_changed(0); self.refresh_table(); self.restore_game_label()
    def restore_game_label(self):
        g = self.settings.get("game", {}); 
        if g.get("exe"): self.game_label.setText(f"{g.get('name', g['exe'])}  ({g['exe']})")
    def curriculum_changed(self, index):
        c = available_curricula()[index]; self.subject.clear(); self.subject.addItems(c.subjects); self.stage.clear(); self.stage.addItems(c.qualification_stages)
    def pick_game(self):
        d = GamePicker(self, self.settings.get("game"))
        if d.exec() and d.selected:
            self.settings["game"] = d.selected; save_settings(self.settings); self.game_label.setText(f"{d.selected['name']}  ({d.selected['exe']})"); self.status.setText("Game selected. Start a session when ready.")
    def course(self):
        c = available_curricula()[self.curr.currentIndex()]; return c.id, self.subject.currentText(), self.stage.currentText()
    def target_info(self):
        g = self.settings.get("game", {}); pid, exe = g.get("pid"), g.get("exe", ""); hwnd, fpid = foreground()
        if hwnd and ((pid and fpid == pid) or (exe and self._foreground_is_exe(fpid, exe))): return hwnd, fpid
        return 0, 0
    def _foreground_is_exe(self, pid, exe):
        try: return norm(psutil.Process(pid).name()) == norm(exe)
        except psutil.Error: return False
    def target_active(self):
        g = self.settings.get("game", {}); return bool(g.get("exe")) and target_is_foreground(g.get("pid"), g.get("exe"))
    def toggle_session(self):
        if self.session: self.stop_session("Session stopped."); return
        g = self.settings.get("game", {})
        if not g.get("exe"): QMessageBox.warning(self, APP_NAME, "Select the game you want StudyLock to monitor first."); return
        cid, subject, stage = self.course(); self.pool = filter_questions(self.questions, curriculum_id=cid, subject=subject, qualification_stage=stage)
        if not self.pool: QMessageBox.warning(self, APP_NAME, "There are no questions for this course yet. Import a question bank first."); return
        self.settings["interval"] = self.interval.value(); save_settings(self.settings)
        self.session = True; self.stats["sessions"] += 1; self.remaining = self.interval.value() * 60; self.last_tick = time.monotonic(); self.start.setText("STOP SESSION"); self.status.setText("Session running. Timer counts only while the selected game is active.")
    def stop_session(self, message):
        self.session = False; self.current = None; self.remaining = 0; self.start.setText("START SESSION"); self.status.setText(message); save_stats(self.stats)
        if self.overlay: self.overlay.allow_close = True; self.overlay.close(); self.overlay = None
    def tick(self):
        now = time.monotonic(); dt = min(1.0, now - self.last_tick); self.last_tick = now
        if not self.session: return
        if self.overlay:
            self.overlay.watch(); return
        if self.target_active():
            self.remaining -= dt
            if self.remaining <= 0: self.trigger_question()
        self.status.setText(f"Session running • next question in {max(0,self.remaining)/60:.1f} min • {self.stage.currentText()} {self.subject.currentText()}")
    def trigger_question(self):
        pool = [q for q in self.pool if q.get("id") != self.last_id] or self.pool; self.current = random.choice(pool); self.last_id = self.current.get("id"); self.overlay = Overlay(self.current, self.answer_question, self.target_info); self.overlay.show()
    def answer_question(self, value, elapsed, wrong_before):
        q = self.current; n = norm(value); correct = False
        for a in q["answers"]:
            if n == norm(a): correct = True; break
            try:
                tol = float(q.get("numeric_tolerance", 0))
                if tol > 0 and abs(float(value) - float(a)) <= tol: correct = True; break
            except (ValueError, TypeError): pass
        key = q["id"]; s = self.stats["questions"].setdefault(key, {"topic":q.get("topic","General"),"attempts":0,"correct":0,"wrong":0,"times":[]}); s["topic"] = q.get("topic","General"); s["attempts"] += 1
        if correct: s["correct"] += 1; s["times"].append(round(elapsed,3))
        else: s["wrong"] += 1
        self.stats["total_answered"] += 1; self.stats["total_correct"] += int(correct); save_stats(self.stats)
        if correct:
            self.overlay = None; self.current = None; self.remaining = self.interval.value() * 60; self.last_tick = time.monotonic(); self.status.setText("Correct! Gameplay unlocked. Timer reset."); return True
        return False
    def recovery_hotkey(self):
        if sys.platform != "win32" or not self.session: return
        try:
            u = ctypes.windll.user32; down = all(u.GetAsyncKeyState(k) & 0x8000 for k in (0x11,0x10,0x7B))
            if down:
                if not hasattr(self,"recovery_since"): self.recovery_since = time.monotonic()
                if time.monotonic() - self.recovery_since >= 5: self.stop_session("Emergency recovery used. Session safely stopped."); self.recovery_since = None
            else: self.recovery_since = None
        except Exception: pass
    def import_questions(self):
        path,_ = QFileDialog.getOpenFileName(self,"Import questions","","JSON files (*.json)")
        if not path: return
        try:
            incoming = validate_questions(json.loads(Path(path).read_text(encoding="utf-8"))); existing = {q["id"]:q for q in self.questions}; existing.update({q["id"]:q for q in incoming}); self.questions = list(existing.values()); atomic_write(QUESTIONS_FILE,{"questions":self.questions}); self.refresh_table(); QMessageBox.information(self,APP_NAME,f"Imported {len(incoming)} questions.")
        except Exception as e: QMessageBox.critical(self,APP_NAME,f"Import failed:\n{e}")
    def export_questions(self):
        path,_ = QFileDialog.getSaveFileName(self,"Export questions","studylock_questions.json","JSON files (*.json)")
        if path:
            try: atomic_write(Path(path),{"questions":self.questions}); QMessageBox.information(self,APP_NAME,"Question bank exported.")
            except Exception as e: QMessageBox.critical(self,APP_NAME,f"Export failed:\n{e}")
    def refresh_table(self):
        if not hasattr(self,"qtable"): return
        self.qtable.setRowCount(0)
        for q in self.questions:
            r = self.qtable.rowCount(); self.qtable.insertRow(r); vals = [q["question"],q["topic"],q["curriculum"],q["subject"],q["qualification_stage"],", ".join(q["answers"])]
            for c,v in enumerate(vals): self.qtable.setItem(r,c,QTableWidgetItem(str(v)))
    def closeEvent(self,e):
        if self.session: self.stop_session("Application closed; session stopped safely.")
        e.accept()

def main():
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); w = MainWindow(); w.show(); sys.exit(app.exec())

if __name__ == "__main__": main()
