from pathlib import Path
import re

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# The previous script used nested triple-quoted strings, which made the script
# itself invalid Python. Keep the stylesheet replacement as a normal string.
style = '''STYLE = """
QWidget { background:#080b10; color:#eef2f7; font-family:"Segoe UI"; font-size:14px; }
QMainWindow { background:#080b10; }
QLabel { background:transparent; }
QFrame#card { background:#101722; border:1px solid #202b3b; border-radius:16px; }
QLabel#title { font-size:32px; font-weight:750; letter-spacing:1px; }
QLabel#subtitle { color:#8995a8; font-size:13px; }
QLabel#muted { color:#8f9bae; }
QLabel#statusPill { background:#151d29; border:1px solid #29364a; border-radius:9px; padding:7px 12px; color:#aeb9ca; font-weight:650; }
QLineEdit, QComboBox, QSpinBox { background:#0b111a; border:1px solid #273346; border-radius:10px; padding:10px; color:#eef2f7; min-height:20px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border:1px solid #607cff; }
QPushButton { background:#151e2b; border:1px solid #2a394d; border-radius:10px; padding:10px 15px; font-weight:650; min-height:18px; }
QPushButton:hover { background:#222f44; border-color:#637fff; }
QPushButton:pressed { background:#31425f; padding-top:11px; padding-bottom:9px; }
QPushButton#primary { background:#526fff; border-color:#7890ff; color:white; }
QPushButton#primary:hover { background:#6681ff; }
QPushButton#danger { background:#22161b; border-color:#56303a; color:#ffb6c0; }
QPushButton#danger:hover { background:#332027; border-color:#b84b60; }
QTableWidget { background:#0c121b; border:1px solid #202b3b; border-radius:10px; gridline-color:#202b3b; }
QHeaderView::section { background:#151d29; padding:9px; border:0; font-weight:700; }
QProgressBar { background:#0b111a; border:1px solid #263347; border-radius:7px; text-align:center; height:12px; }
QProgressBar::chunk { background:#607cff; border-radius:6px; }
"""
'''
s = re.sub(r'STYLE\s*=\s*""".*?"""', style.rstrip(), s, count=1, flags=re.S)

# Keep the answer-button polish self-contained and syntactically simple.
answer = '''class AnswerButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(self.idle())

    def idle(self):
        return ("QPushButton{background:rgba(18,27,40,238);border:1px solid rgba(119,140,177,78);"
                "border-radius:14px;padding:10px 18px;text-align:left;font-size:16px;} "
                "QPushButton:hover{background:rgba(58,76,119,248);border:1px solid rgba(127,151,255,235);padding-left:22px;} "
                "QPushButton:pressed{background:rgba(92,124,255,255);border:1px solid rgba(180,195,255,255);padding-left:25px;}")
'''
s = re.sub(r'class AnswerButton\(QPushButton\):.*?(?=\nclass Overlay)', answer.rstrip(), s, count=1, flags=re.S)

# Make the lock animation reach the actual screen corners and raise the question card.
lock = '''class LockChain(QWidget):
    def __init__(self, parent=None, reduced=False):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.reduced = reduced
        self.progress = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)

    def start(self):
        self.progress = 0.0
        self.show()
        self.raise_()
        if self.reduced:
            self.progress = 1.0
            self.update()
            QTimer.singleShot(220, self.finish)
        else:
            self.timer.start(16)

    def step(self):
        self.progress = min(1.0, self.progress + 0.028)
        self.update()
        if self.progress >= 1.0:
            self.timer.stop()
            QTimer.singleShot(180, self.finish)

    def finish(self):
        self.hide()
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        center = QPointF(w / 2, h / 2)
        inset = 8
        corners = [
            QPointF(inset, inset), QPointF(w - inset, inset),
            QPointF(inset, h - inset), QPointF(w - inset, h - inset),
        ]
        painter.setPen(QPen(QColor(95, 126, 255, 205), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for end in corners:
            t = min(1.0, max(0.0, self.progress * 1.12))
            current = QPointF(center.x() + (end.x() - center.x()) * t,
                              center.y() + (end.y() - center.y()) * t)
            painter.drawLine(center, current)
            if t > 0.08:
                r = 25
                painter.setBrush(QBrush(QColor(17, 23, 34, 245)))
                painter.setPen(QPen(QColor(125, 149, 255, 240), 2))
                painter.drawRoundedRect(int(current.x() - r), int(current.y() - r), r * 2, r * 2, 9, 9)
                painter.setPen(QPen(QColor(235, 240, 250, 235), 3))
                painter.drawArc(int(current.x() - 8), int(current.y() - 13), 16, 19, 0, 180 * 16)
                painter.drawRect(int(current.x() - 9), int(current.y() - 3), 18, 13)

        if self.progress > 0.32:
            rise = min(1.0, (self.progress - 0.32) / 0.68)
            eased = 1 - (1 - rise) ** 3
            card_w = min(760, w - 160)
            card_h = 120
            y = h / 2 + 220 - (260 * eased)
            alpha = int(255 * min(1, rise * 1.5))
            painter.setBrush(QBrush(QColor(17, 24, 36, alpha)))
            painter.setPen(QPen(QColor(110, 135, 255, alpha), 2))
            painter.drawRoundedRect(int(center.x() - card_w / 2), int(y - card_h / 2), card_w, card_h, 20, 20)
            painter.setPen(QPen(QColor(235, 240, 250, alpha), 2))
            painter.setFont(QFont("Segoe UI", 18, QFont.Weight.DemiBold))
            painter.drawText(int(center.x() - card_w / 2), int(y - 12), card_w, 32,
                             Qt.AlignmentFlag.AlignCenter, "QUESTION LOCKED")
            painter.setPen(QPen(QColor(145, 158, 182, alpha), 1))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(int(center.x() - card_w / 2), int(y + 17), card_w, 24,
                             Qt.AlignmentFlag.AlignCenter, "Answer correctly to continue")
'''
s = re.sub(r'class LockChain\(QWidget\):.*?(?=\nclass AnswerButton)', lock.rstrip(), s, count=1, flags=re.S)

s = s.replace("self.start.setText('RUNNING'); self.status.setText('Running');",
              "self.start.setText('STOP STUDYLOCK'); self.status.setText('RUNNING'); self.status.setObjectName('statusPill'); self.status.style().unpolish(self.status); self.status.style().polish(self.status);")
s = s.replace("self.status.setText('Stopped'); self.start.setText('START STUDYLOCK')",
              "self.status.setText('STOPPED'); self.start.setText('START STUDYLOCK'); self.status.setObjectName('statusPill'); self.status.style().unpolish(self.status); self.status.style().polish(self.status)")
s = s.replace("screen=QApplication.screenAt(QPointF(0,0).toPoint()) or QApplication.primaryScreen();",
              "r=window_rect(h) if h else None; screen=QApplication.screenAt(r.center()) if r else QApplication.primaryScreen(); screen=screen or QApplication.primaryScreen();")
s = s.replace("root=QWidget(); outer=QVBoxLayout(root); outer.setContentsMargins(30,26,30,26); outer.setSpacing(18)\n        head=QHBoxLayout(); title=QLabel(APP_NAME); title.setObjectName('title'); head.addWidget(title); head.addStretch(); self.status=QLabel('Stopped'); self.status.setObjectName('muted'); head.addWidget(self.status); outer.addLayout(head)",
              "root=QWidget(); outer=QVBoxLayout(root); outer.setContentsMargins(28,24,28,24); outer.setSpacing(16)\n        head=QHBoxLayout(); head.setSpacing(14); titlebox=QVBoxLayout(); title=QLabel(APP_NAME); title.setObjectName('title'); titlebox.addWidget(title); sub=QLabel('Focus mode for serious study — your game stays untouched.'); sub.setObjectName('subtitle'); titlebox.addWidget(sub); head.addLayout(titlebox); head.addStretch(); self.status=QLabel('STOPPED'); self.status.setObjectName('statusPill'); head.addWidget(self.status,0,Qt.AlignmentFlag.AlignTop); outer.addLayout(head)")
s = s.replace("g.setContentsMargins(20,20,20,20); g.setHorizontalSpacing(12); g.setVerticalSpacing(12)",
              "g.setContentsMargins(20,20,20,20); g.setHorizontalSpacing(14); g.setVerticalSpacing(9)\n        for i in range(4): g.setColumnStretch(i,1)")
s = s.replace("stop=QPushButton('Stop'); stop.clicked.connect(self.stop); actions.addWidget(stop);",
              "stop=QPushButton('Stop session'); stop.setObjectName('danger'); stop.clicked.connect(self.stop); actions.addWidget(stop);")
p.write_text(s, encoding="utf-8")
